# SPDX-License-Identifier: Apache-2.0
# Adapted from Enable Banking API samples, account_information.py.
# Upstream: Enable Banking contributors, no source-file copyright line supplied.
# Modifications Copyright 2026 Marco Antonio Tevar Asensio.
# Changed 2026-11-19: pure offline admin protocol, bounded callbacks,
# one-use constant-time state, monotonic TTL, no printing or network defaults.
"""Offline setup building blocks. NOT an MCP tool or a live bank integration.

Upstream AIS sequence: POST /auth, user authorizes, POST /sessions.
Caller owns the explicit admin workflow and must keep codes/session data private.
Production localhost acceptance is UNCONFIRMED. No application is registered here.
"""
from __future__ import annotations

import hmac
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlsplit


class SetupRejected(ValueError):
    """Intentionally value-free public error."""


def _reject() -> None:
    raise SetupRejected("Setup request rejected") from None


def validate_redirect(redirect: str) -> str:
    # One explicitly chosen URI, no arbitrary host, credentials, fragments,
    # percent-encoded authority or browser-specific localhost aliases.
    if type(redirect) is not str or redirect != "https://localhost:8765/callback":
        _reject()
    return redirect


class ConsentAttempt:
    """One private in-memory authorization attempt. No code/state in repr.

    The deadline covers the browser callback, not provider session lifetime.
    A valid error callback consumes the attempt. Bad/unrelated traffic does not.
    Use one instance per admin attempt; never expose it through MCP or logging.
    Not thread safe: the HTTP listener must serialize handling.
    """
    __slots__ = ("_redirect", "_state", "_deadline", "_clock", "_used")

    def __init__(self, redirect: str, *, ttl_seconds: int = 300, clock=time.monotonic):
        self._redirect = validate_redirect(redirect)
        if type(ttl_seconds) is not int or not 30 <= ttl_seconds <= 300:
            _reject()
        self._state = secrets.token_urlsafe(32)
        self._clock = clock
        self._deadline = clock() + ttl_seconds
        self._used = False

    def __repr__(self):
        return "<ConsentAttempt private>"

    def _active(self):
        if self._used or self._clock() >= self._deadline:
            self._state = ""
            self._used = True
            _reject()

    def authorization_body(self, bank_name: str, country: str, *, now: datetime,
                           access_seconds: int = 3600) -> dict:
        self._active()
        if (type(bank_name) is not str or not 1 <= len(bank_name) <= 120
                or any(ord(c) < 32 for c in bank_name)
                or type(country) is not str or re.fullmatch(r"[A-Z]{2}", country) is None
                or type(access_seconds) is not int or not 60 <= access_seconds <= 86400
                or not isinstance(now, datetime) or now.tzinfo is None
                or now.utcoffset() is None):
            _reject()
        # Bank/country must be selected from live provider discovery by the
        # caller/user. This builder deliberately has no default bank or country.
        until = (now.astimezone(timezone.utc) + timedelta(seconds=access_seconds)).isoformat()
        return {"access": {"valid_until": until},
                "aspsp": {"name": bank_name, "country": country},
                "state": self._state, "redirect_url": self._redirect, "psu_type": "personal"}

    def consume_callback(self, full_url: str) -> dict:
        """Return a private POST /sessions body. Never log the result.

        Only the local listener reconstructs full_url from a fixed origin plus
        request target. Never trust Host or forwarded headers for that origin.
        """
        self._active()
        if (type(full_url) is not str or len(full_url) > 8192
                or any(ord(c) < 33 or ord(c) > 126 for c in full_url)):
            _reject()
        try:
            parsed = urlsplit(full_url)
            expected = urlsplit(self._redirect)
            if (parsed.scheme != expected.scheme or parsed.netloc != expected.netloc
                    or parsed.path != expected.path or parsed.fragment
                    or not parsed.query or re.search(r"%(?![0-9A-Fa-f]{2})", parsed.query)):
                _reject()
            pairs = parse_qsl(parsed.query, keep_blank_values=True,
                              strict_parsing=True, max_num_fields=4,
                              encoding="utf-8", errors="strict")
        except (ValueError, UnicodeError):
            _reject()
        data = dict(pairs)
        if (len(data) != len(pairs) or not set(data) <= {"state", "code", "error", "error_description"}
                or set(data) not in ({"state", "code"}, {"state", "error"},
                                     {"state", "error", "error_description"})):
            _reject()
        state = data["state"]
        if (not state.isascii() or not hmac.compare_digest(state, self._state)):
            _reject()
        self._used = True
        self._state = ""
        if "error" in data:
            _reject()  # Do not retain/display untrusted provider error descriptions.
        code = data["code"]
        if not 1 <= len(code) <= 4096 or not code.isascii() or any(ord(c) < 33 or ord(c) == 127 for c in code):
            _reject()
        # Recheck after parsing as well. Parsing must never extend the TTL.
        if self._clock() >= self._deadline:
            _reject()
        return {"code": code}

    @property
    def remaining_seconds(self):
        """Remaining monotonic lifetime for a private listener's shutdown timer."""
        return 0.0 if self._used else max(0.0, self._deadline-self._clock())

    @property
    def closed(self):
        """Public lifecycle flag, no state/code. Expiry closes on next check."""
        return self._used or self._clock() >= self._deadline

    def cancel(self):
        self._used = True
        self._state = ""
