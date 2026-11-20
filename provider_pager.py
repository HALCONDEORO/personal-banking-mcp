"""Bounded AIS pagination with an injected async transport, synthetic testing only.

Not wired to the MCP. No network implementation, keys or consent. A future real
transport must refuse redirects, cap streaming response bytes before buffering,
set connect/read timeouts and never log headers or response bodies.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import date
import json
import math
import re
import time
from typing import Awaitable, Callable
from uuid import UUID
from async_boundary import _await_owned
from provider_normalize import InvalidProviderData, normalize_page

HOST = 'https://api.enablebanking.com'

class FetchStopped(ValueError):
    """Safe error code only, no private provider payload."""

@dataclass(frozen=True)
class ReadRequest:
    host: str
    path: str
    query: tuple[tuple[str, str], ...]

@dataclass(frozen=True)
class FakeResponse:
    status: int
    body: bytes

@dataclass(frozen=True)
class Limits:
    pages: int = 10
    rows: int = 500
    bytes_total: int = 256_000
    seconds: float = 5.0


def _strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FetchStopped('invalid_response')
        result[key] = value
    return result


def _no_constant(_):
    raise FetchStopped('invalid_response')


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise FetchStopped('invalid_response')
    return value


def _strict_response_json(raw):
    """Reject duplicate keys and every nonfinite number, including exponents.

    parse_constant alone does not catch JSON `1e999`, which Python converts to inf.
    Provider amount fields remain decimal strings validated by normalization;
    finite numeric extras are accepted and discarded under the existing schema.
    """
    return json.loads(raw, object_pairs_hook=_strict_object,
                      parse_constant=_no_constant, parse_float=_finite_float)


def _check_limits(limits):
    if not isinstance(limits, Limits):
        raise ValueError('Invalid local limits')
    for value, maximum in ((limits.pages, 50), (limits.rows, 5000), (limits.bytes_total, 1_000_000)):
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError('Invalid local limits')
    if type(limits.seconds) not in {int, float} or not 0 < limits.seconds <= 30:
        raise ValueError('Invalid local limits')


def _dates(start, end):
    if any(not isinstance(v, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', v) for v in (start, end)):
        raise ValueError('Invalid date range')
    try:
        span = (date.fromisoformat(end) - date.fromisoformat(start)).days
    except ValueError:
        raise ValueError('Invalid date range') from None
    if not 0 <= span <= 365:
        raise ValueError('Invalid date range')


async def fetch_simulated_transactions(
    account: str, authorized_accounts: frozenset[str], start: str, end: str,
    transport: Callable[[ReadRequest], Awaitable[FakeResponse]], *,
    limits: Limits = Limits(),
) -> dict:
    """Return all pages or a safe error, never a falsely complete partial result.

    Only owner-authorized UUIDs reach transport. Query dates remain unchanged.
    A cursor can only populate the query, never the host or path. HTTP failures
    are not retried automatically, especially429. Time budget is enforced around
    each await; a future transport must cooperate with cancellation.
    """
    _check_limits(limits)
    _dates(start, end)
    if not isinstance(account, str) or not isinstance(authorized_accounts, frozenset) or account not in authorized_accounts:
        raise ValueError('Account not authorized')
    try:
        if str(UUID(account)) != account:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('Account not authorized') from None
    deadline = time.monotonic() + limits.seconds
    rows, seen_cursors, seen_refs = [], set(), set()
    cursor, total_bytes = None, 0
    for page_number in range(1, limits.pages + 1):
        query = [('date_from', start), ('date_to', end), ('strategy', 'longest')]
        if cursor is not None:
            query.append(('continuation_key', cursor))
        request = ReadRequest(HOST, f'/accounts/{account}/transactions', tuple(query))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise FetchStopped('time_budget')
        try:
            response = await _await_owned(transport(request), remaining)
        except asyncio.TimeoutError:
            raise FetchStopped('time_budget') from None
        except Exception:
            raise FetchStopped('transport_failure') from None
        if time.monotonic() > deadline:
            raise FetchStopped('time_budget')
        if not isinstance(response, FakeResponse) or type(response.status) is not int or not isinstance(response.body, bytes):
            raise FetchStopped('invalid_response')
        codes = {401:'reconnect_required',403:'access_denied',422:'request_rejected',429:'rate_limited',500:'provider_unavailable'}
        if response.status != 200:
            raise FetchStopped(codes.get(response.status, 'unexpected_status'))
        total_bytes += len(response.body)
        if total_bytes > limits.bytes_total:
            raise FetchStopped('byte_budget')
        try:
            payload = _strict_response_json(response.body)
            page = normalize_page(payload)
        except (ValueError, UnicodeError, RecursionError):
            raise FetchStopped('invalid_response') from None
        if time.monotonic() > deadline:
            raise FetchStopped('time_budget')
        for raw in payload['transactions']:
            reference = raw.get('entry_reference')
            if reference is not None:
                if not isinstance(reference, str) or not 1 <= len(reference) <= 256:
                    raise FetchStopped('invalid_response')
                if reference in seen_refs:
                    # Refuse ambiguity; do not silently drop a potentially different entry.
                    raise FetchStopped('duplicate_reference')
                seen_refs.add(reference)
        rows.extend(page['transactions'])
        if len(rows) > limits.rows:
            raise FetchStopped('row_budget')
        cursor = page['continuation_key']
        if time.monotonic() > deadline:
            raise FetchStopped('time_budget')
        if cursor is None:
            return {'source':'simulated-provider', 'live':False, 'transactions':rows,
                    'provider_pagination_complete':True, 'history_complete':False,
                    'pages':page_number,
                    'note':'Provider pagination exhaustion is not proof of full bank history; no bank connected'}
        if cursor in seen_cursors:
            raise FetchStopped('cursor_loop')
        seen_cursors.add(cursor)
    raise FetchStopped('page_budget')
