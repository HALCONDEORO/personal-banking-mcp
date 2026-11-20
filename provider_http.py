"""Opt-in HTTP read transport experiment. Not registered in the fixture MCP.

Tests use httpx.MockTransport only. Application setup and consent are outside this
module. No payments, POST, arbitrary URLs, proxy environment, redirects or retries.
"""
import logging
import asyncio
import re
import time
from uuid import UUID
from typing import Callable
import httpx
import jwt
from provider_pager import FakeResponse, FetchStopped, ReadRequest, HOST

_ACCOUNT_PATH = re.compile(r'/accounts/([0-9a-f-]{36})/(details|balances|transactions)\Z')
_SESSION_PATH = re.compile(r'/sessions/([0-9a-f-]{36})\Z')


def application_jwt(application_id: str, private_key: bytes, *, now: int | None = None) -> str:
    """Sign a short-lived application JWT, without reading or printing key files."""
    try:
        if str(UUID(application_id)) != application_id:
            raise ValueError
        if not isinstance(private_key, bytes) or len(private_key) > 32_768:
            raise ValueError
        issued = int(time.time()) if now is None else now
        if type(issued) is not int or issued < 0:
            raise ValueError
        return jwt.encode({'iss':'enablebanking.com','aud':'api.enablebanking.com',
                           'iat':issued,'exp':issued+300}, private_key,
                          algorithm='RS256',headers={'kid':application_id})
    except Exception:
        raise ValueError('Application key configuration invalid') from None


def validate_read_request(request, *, accounts, session):
    if not isinstance(request, ReadRequest) or request.host != HOST:
        raise FetchStopped('operation_denied')
    account_match = _ACCOUNT_PATH.fullmatch(request.path)
    session_match = _SESSION_PATH.fullmatch(request.path)
    if account_match:
        if account_match[1] not in accounts:
            raise FetchStopped('operation_denied')
    elif not session_match or session_match[1] != session:
        raise FetchStopped('operation_denied')
    if not isinstance(request.query, tuple) or len(request.query) > 5:
        raise FetchStopped('operation_denied')
    seen=set()
    for entry in request.query:
        if not isinstance(entry,tuple) or len(entry)!=2:
            raise FetchStopped('operation_denied')
        key,value=entry
        if not isinstance(key,str) or key in seen or not isinstance(value,str) or len(value)>2048 or any(ord(c)<32 for c in value):
            raise FetchStopped('operation_denied')
        seen.add(key)
        if not account_match or account_match[2]!='transactions' or key not in {'date_from','date_to','continuation_key','transaction_status','strategy'}:
            raise FetchStopped('operation_denied')
        if key=='strategy' and value != 'longest':
            raise FetchStopped('operation_denied')
        if key=='transaction_status' and value not in {'BOOK','PDNG'}:
            raise FetchStopped('operation_denied')
    # Dates and date-span bounds are enforced by the pager before transport.
    # This transport also validates date syntax to protect independent use.
    from datetime import date
    for key,value in request.query:
        if key in {'date_from','date_to'}:
            try:
                if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value): raise ValueError
                date.fromisoformat(value)
            except ValueError:
                raise FetchStopped('operation_denied') from None



class _NoProviderDiagnostics(logging.Filter):
    def filter(self, record):
        return not (record.name in {'httpx', 'httpcore'} or record.name.startswith(('httpx.', 'httpcore.')))


def suppress_provider_diagnostics():
    """Attach namespace filters to output handlers, including root and lastResort.

    Handler filters see descendant records, including loggers created later.
    Persistent opt-in process policy: the application must call this after any
    logging reconfiguration that adds/replaces handlers. We call it again before
    every request. No monkeypatch of logging APIs. Unrelated logs remain intact.
    """
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    loggers = [root] + [obj for obj in logging.root.manager.loggerDict.values()
                       if isinstance(obj, logging.Logger)]
    handlers = {handler for logger in loggers for handler in logger.handlers}
    if logging.lastResort is not None:
        handlers.add(logging.lastResort)
    for handler in handlers:
        if not any(isinstance(f, _NoProviderDiagnostics) for f in handler.filters):
            handler.addFilter(_NoProviderDiagnostics())


def _retrieve_request_result(task):
    # Also retrieve a result after repeated caller cancellation interrupts drain.
    if not task.cancelled():
        task.exception()


async def _await_request(coro, seconds):
    """Keep caller cancellation/timeout separate from transport cleanup failures.

    Drain cancellation cooperatively, as wait_for already does. This is not a
    hard wall-clock bound for a transport that refuses to finish cleanup.
    """
    task = asyncio.create_task(coro)
    task.add_done_callback(_retrieve_request_result)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=seconds)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        task.cancel()
        try:
            await task
        except (Exception, asyncio.CancelledError):
            pass
        raise


class ReadOnlyHTTP:
    """Narrow provider client. Constructing it performs no I/O.

    authorized_accounts/session must come from human-approved setup, not tool
    arguments. Token is requested only after validating destination and scope.
    No automatic retry. Caller owns pagination, consent expiry and rate policy.
    A network call occurs only on an explicit awaited request; fixture MCP never
    constructs this object. A real use still requires user authority and review.
    """
    def __init__(self, token: Callable[[], str], *, accounts: frozenset[str],
                 session: str, max_bytes: int = 256_000, total_seconds: float = 5.0,
                 _test_transport: httpx.AsyncBaseTransport | None = None):
        if type(max_bytes) is not int or not 1 <= max_bytes <= 1_000_000:
            raise ValueError('Invalid byte limit')
        ids = list(accounts) + [session] if isinstance(accounts, frozenset) else []
        if not ids or any(not isinstance(v,str) or str(UUID(v)) != v for v in ids):
            raise ValueError('Invalid authorization scope')
        if type(total_seconds) not in {int,float} or not 0 < total_seconds <= 5:
            raise ValueError('Invalid total time limit')
        self._total_seconds = total_seconds
        self._token, self._accounts, self._session = token, accounts, session
        self._max_bytes, self._transport = max_bytes, _test_transport
        suppress_provider_diagnostics()

    def _validate(self, request):
        validate_read_request(request, accounts=self._accounts, session=self._session)

    async def __call__(self, request: ReadRequest) -> FakeResponse:
        self._validate(request)
        deadline = time.monotonic() + self._total_seconds
        try:
            result = await _await_request(self._read(request, deadline), self._total_seconds)
        except asyncio.TimeoutError:
            raise FetchStopped('time_budget') from None
        # A transport or cleanup routine can suppress cancellation. Never accept
        # a late success just because wait_for eventually returned a value.
        if time.monotonic() >= deadline:
            raise FetchStopped('time_budget')
        return result

    async def _read(self, request: ReadRequest, deadline: float) -> FakeResponse:
        def check_deadline():
            if time.monotonic() >= deadline:
                raise FetchStopped('time_budget')
        try:
            token = self._token()
            check_deadline()
            if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',token) or len(token)>16_384:
                raise ValueError
            async with httpx.AsyncClient(transport=self._transport,trust_env=False,
                                         follow_redirects=False,timeout=httpx.Timeout(5.0,connect=3.0),
                                         limits=httpx.Limits(max_connections=1,max_keepalive_connections=0)) as client:
                suppress_provider_diagnostics()
                async with client.stream('GET',HOST+request.path,params=request.query,
                                         headers={'Authorization':'Bearer '+token,'Accept':'application/json','Accept-Encoding':'identity'}) as response:
                    check_deadline()
                    if response.status_code != 200:
                        # Do not read or echo private error bodies or redirect destinations.
                        return FakeResponse(response.status_code,b'')
                    encoding=response.headers.get('content-encoding','identity').strip().lower()
                    if encoding != 'identity':
                        raise FetchStopped('content_encoding_denied')
                    kind=response.headers.get('content-type','').split(';')[0].strip().lower()
                    if kind!='application/json':
                        raise FetchStopped('invalid_content_type')
                    length=response.headers.get('content-length')
                    if length is not None and (not length.isascii() or not length.isdigit() or int(length)>self._max_bytes):
                        raise FetchStopped('byte_budget')
                    data=bytearray()
                    async for chunk in response.aiter_raw(chunk_size=8192):
                        check_deadline()
                        if len(data)+len(chunk)>self._max_bytes:
                            raise FetchStopped('byte_budget')
                        data.extend(chunk)
                    check_deadline()
                    return FakeResponse(200,bytes(data))
        except FetchStopped:
            raise
        except Exception:
            raise FetchStopped('read_failed') from None
