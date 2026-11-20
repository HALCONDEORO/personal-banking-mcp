# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Isolated session-check composition. No network defaults, MCP or setup effects."""
import asyncio
from datetime import datetime, timezone
import re
from provider_pager import ReadRequest, FakeResponse, HOST, _strict_response_json
from async_boundary import _await_owned
from provider_session import PrivateSession, _time, _uuid


class SessionReadStopped(ValueError):
    def __init__(self):
        super().__init__('Session read stopped')


def _reject():
    raise SessionReadStopped() from None


def validate_session_check(payload, *, expected_accounts, bank, country, now):
    """Require provider AUTHORIZED state and all locally selected accounts.

    Additional provider accounts are never adopted. A matching UUID/status is
    not proof of account ownership or future consent validity.
    """
    if (type(payload) is not dict or payload.get('status') != 'AUTHORIZED'
            or payload.get('psu_type') != 'personal'
            or payload.get('closed') is not None
            or type(payload.get('aspsp')) is not dict
            or payload['aspsp'].get('name') != bank
            or payload['aspsp'].get('country') != country
            or type(payload.get('access')) is not dict):
        _reject()
    try:
        until = _time(payload['access'].get('valid_until'))
        if until <= now:
            _reject()
        accounts = payload.get('accounts')
        if type(accounts) is not list or not 1 <= len(accounts) <= 50:
            _reject()
        ids = tuple(_uuid(x) for x in accounts)
        if len(set(ids)) != len(ids) or not set(expected_accounts) <= set(ids):
            _reject()
    except Exception:
        _reject()
    return until


class CheckedSessionRead:
    """Validate session immediately before each narrowly scoped account read.

    Inject a trusted read-only transport and one already validated private
    session. Never create these from MCP/user-supplied arguments. One instance
    serializes its workflows, not other instances/processes. No cached proof,
    retry, renewal, persistence, JWT creation or credential access here.
    """
    def __init__(self, *, session, bank, country, transport, now=lambda: datetime.now(timezone.utc), seconds=5):
        if (type(session) is not PrivateSession or not callable(transport)
                or not callable(now) or type(bank) is not str or not 1 <= len(bank) <= 120
                or any(ord(c) < 32 for c in bank)
                or type(country) is not str or re.fullmatch('[A-Z]{2}', country) is None
                or type(seconds) not in (int, float) or not 0 < seconds <= 5):
            _reject()
        self._session, self._bank, self._country = session, bank, country
        self._transport, self._now, self._seconds = transport, now, seconds
        self._lock = asyncio.Lock()

    def __repr__(self):
        return '<CheckedSessionRead private>'

    def _scope(self):
        now = self._now()
        if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
            _reject()
        return now.astimezone(timezone.utc), self._session.transport_ids(now=now)

    async def __call__(self, request):
        # Validate BEFORE any provider call, token retrieval or waiting for lock.
        failed = False
        try:
            _, (_, accounts) = self._scope()
            if type(request) is not ReadRequest or request.host != HOST:
                _reject()
            match = re.fullmatch(r'/accounts/([0-9a-f-]{36})/(details|balances|transactions)', request.path)
            if not match or match[1] not in accounts:
                _reject()
            # Reuse the transport's pure allowlist validation, never construct a
            # network client or invoke a credential supplier to validate shape.
            from provider_http import validate_read_request
            validate_read_request(request, accounts=frozenset(accounts), session=self._session.transport_ids(now=self._now())[0])
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self._seconds
            result = await _await_owned(self._workflow(request, deadline), self._seconds)
            if loop.time() >= deadline:
                _reject()
            return result
        except asyncio.CancelledError:
            raise
        except Exception:
            failed = True
        if failed:
            _reject()

    async def _workflow(self, request, deadline):
        def in_time():
            if asyncio.get_running_loop().time() >= deadline:
                _reject()
        async with self._lock:
            in_time()
            _, (sid, accounts) = self._scope()
            response = await _await_owned(
                self._transport(ReadRequest(HOST, '/sessions/' + sid, ())),
                max(0, deadline - asyncio.get_running_loop().time()))
            in_time()
            now, _ = self._scope()
            if (type(response) is not FakeResponse or type(response.status) is not int
                    or response.status != 200 or type(response.body) is not bytes
                    or len(response.body) > 65536):
                _reject()
            payload = _strict_response_json(response.body)
            until = validate_session_check(payload, expected_accounts=accounts, bank=self._bank, country=self._country, now=now)
            now, _ = self._scope()
            if now >= until:
                _reject()
            in_time()
            result = await _await_owned(
                self._transport(request),
                max(0, deadline - asyncio.get_running_loop().time()))
            in_time()
            now, _ = self._scope()
            if now >= until:
                _reject()
            if type(result) is not FakeResponse:
                _reject()
            return result
