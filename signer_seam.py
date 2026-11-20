# SPDX-License-Identifier: MIT
"""Fixed, in-process signer seam for the read-only transport. No I/O of its own.

This is an adapter, not a signer and not a signing service. It wraps ONE backend
callable that the owner's private, reviewed local setup supplies. The backend takes
no arguments, so the adapter exposes no way to choose claims, data, destination or
key. The adapter checks that what comes back has the one fixed token shape and then
hands the string to the transport. It does not verify the signature, prove key
custody, or prove the provider will accept the token. There is no CLI, network
listener, stdout or HTTP surface here, and tokens never go into repr, errors or logs.
"""
import base64
import json
import re
import threading
import time
from typing import Callable
from uuid import UUID

ISSUER = 'enablebanking.com'
AUDIENCE = 'api.enablebanking.com'
ALGORITHM = 'RS256'
MAX_LIFETIME_SECONDS = 300
MAX_TOKEN_CHARS = 16_384
_SEGMENTS = re.compile(r'[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+')


class SignerSeamError(Exception):
    """Generic failure. Carries no token, claim or backend detail."""
    def __init__(self):
        super().__init__('Signer unavailable')


def _segment(text: str) -> dict:
    raw = base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))
    value = json.loads(raw, parse_constant=_reject_constant)
    if type(value) is not dict:
        raise ValueError
    return value


def _reject_constant(_):
    raise ValueError


def _int(value) -> bool:
    return type(value) is int and 0 <= value < 2**40


def check_token_shape(token, application_id: str, *, now: float) -> None:
    """Raise ValueError unless token has exactly the fixed header and claims."""
    if type(token) is not str or len(token) > MAX_TOKEN_CHARS or not _SEGMENTS.fullmatch(token):
        raise ValueError
    head, body, _sig = token.split('.')
    header, claims = _segment(head), _segment(body)
    if header.get('alg') != ALGORITHM or header.get('kid') != application_id:
        raise ValueError
    if set(header) - {'alg', 'kid', 'typ'} or header.get('typ', 'JWT') != 'JWT':
        raise ValueError
    if set(claims) != {'iss', 'aud', 'iat', 'exp'}:
        raise ValueError
    if claims['iss'] != ISSUER or claims['aud'] != AUDIENCE:
        raise ValueError
    if not _int(claims['iat']) or not _int(claims['exp']):
        raise ValueError
    if not 0 < claims['exp'] - claims['iat'] <= MAX_LIFETIME_SECONDS:
        raise ValueError
    # Not already expired, and not issued meaningfully in the future.
    if claims['exp'] <= now or claims['iat'] > now + 30:
        raise ValueError


class FixedSigner:
    """Callable returning a checked token string, for ReadOnlyHTTP(token=...).

    backend: zero-argument callable from reviewed private local configuration.
    One call at a time; a second concurrent call fails instead of queueing.
    No retry, no caching: a backend failure is final for that request.
    """
    __slots__ = ('_backend', '_application_id', '_clock', '_lock')

    def __init__(self, backend: Callable[[], str], application_id: str, *,
                 _clock: Callable[[], float] = time.time):
        try:
            if not callable(backend) or str(UUID(application_id)) != application_id:
                raise ValueError
        except Exception:
            raise SignerSeamError() from None
        self._backend, self._application_id = backend, application_id
        self._clock, self._lock = _clock, threading.Lock()

    def __call__(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise SignerSeamError()
        ok = False
        try:
            try:
                token = self._backend()
                check_token_shape(token, self._application_id, now=self._clock())
                ok = True
            except BaseException as exc:
                if not isinstance(exc, Exception):
                    raise
        finally:
            self._lock.release()
        # Raised outside the except block so no backend error stays chained.
        if not ok:
            raise SignerSeamError()
        return token

    def __repr__(self) -> str:
        return 'FixedSigner()'

    def __reduce__(self):
        raise TypeError('not serializable')
