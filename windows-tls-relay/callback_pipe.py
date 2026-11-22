# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Synthetic .NET parser -> private inherited pipe -> real ConsentAttempt.

NOT a production receiver/launcher, TLS ACK, relay replacement or bank adapter.
Only invented callbacks generated here are accepted as inputs to the fixture.
No callback/state/code goes into argv, environment, stdout or public errors.
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import struct
import time
from urllib.parse import urlencode

from admin_consent import ConsentAttempt
from callback_framing import ORIGIN
from relay_process import _environment, _join_cleanup, _reap, _seconds


class DataStopped(ValueError):
    def __init__(self):
        super().__init__('Private callback stopped')


_MODES = frozenset({'complete', 'early', 'bad-magic', 'oversize', 'truncated',
                    'duplicate', 'trailing', 'nonzero', 'hold', 'flood',
                    'wrong-state', 'bad-ascii', 'denied', 'wrong-host', 'encoded'})


def _input_frame(request):
    if type(request) is not bytes or not 1 <= len(request) <= 12288:
        raise DataStopped()
    return b'PBI1' + struct.pack('!I', len(request)) + request


async def _read_target(reader, bounded):
    header = await bounded(reader.readexactly(8))
    if header[:4] != b'PBD1':
        raise DataStopped()
    size = struct.unpack('!I', header[4:])[0]
    # ConsentAttempt bounds the complete URL, including the fixed origin.
    if not 1 <= size <= 8192 - len(ORIGIN):
        raise DataStopped()
    raw = await bounded(reader.readexactly(size))
    if await bounded(reader.read(1)) != b'':
        raise DataStopped()
    target = raw.decode('ascii')
    if not target.startswith('/callback?') or any(ord(c) < 33 or ord(c) > 126 for c in target):
        raise DataStopped()
    return ORIGIN + target


class SyntheticDataRunner:
    """One-shot cross-language data proof with a fresh, invented consent attempt.

    Caller supplies only a trusted absolute .NET runtime path and timeout. The
    fixed bundled assembly and mode allowlist are not arbitrary command input.
    Output is a private synthetic session-body dict, never a real provider call.
    Trust assumptions and direct-child cleanup are those of relay_process.
    """
    __slots__ = ('_runtime', '_assembly', '_timeout', '_mode', '_used')

    def __init__(self, runtime, *, timeout=5, _mode='complete'):
        try:
            runtime = Path(runtime)
            if not runtime.is_absolute() or not runtime.is_file() or _mode not in _MODES:
                raise ValueError
            self._assembly = Path(__file__).resolve().parent / 'DataFixture' / 'bin' / 'Release' / 'net10.0' / 'DataFixture.dll'
            if not self._assembly.is_file():
                raise ValueError
            self._runtime, self._timeout = str(runtime.resolve()), _seconds(timeout)
            self._mode, self._used = _mode, False
        except Exception:
            raise DataStopped() from None

    def __repr__(self):
        return '<SyntheticDataRunner private>'

    async def __call__(self):
        if self._used:
            raise DataStopped()
        self._used = True
        deadline = time.monotonic() + self._timeout
        attempt = ConsentAttempt(ORIGIN + '/callback')
        child = None
        cancelled = failed = False
        callback = None

        async def bounded(awaitable):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                awaitable.close()
                raise DataStopped()
            result = await asyncio.wait_for(awaitable, remaining)
            if time.monotonic() >= deadline:
                raise DataStopped()
            return result

        try:
            # Only invented data is constructed here. No external callback API.
            body = attempt.authorization_body('Synthetic fixture only', 'IE', now=datetime.now(timezone.utc))
            query = {'state': body['state']}
            query.update({'error': 'synthetic-denied'} if self._mode == 'denied'
                         else {'code': 'synthetic+/%code' if self._mode == 'encoded' else 'synthetic-private-code'})
            host = 'evil.invalid' if self._mode == 'wrong-host' else 'localhost:8765'
            request = ('GET /callback?' + urlencode(query) + ' HTTP/1.1\r\nHost: ' + host + '\r\n\r\n').encode('ascii')
            mode = 'complete' if self._mode in {'denied', 'wrong-host', 'encoded'} else self._mode
            # Shield acquisition so cancellation cannot lose a spawned child.
            launch = asyncio.create_task(asyncio.create_subprocess_exec(
                self._runtime, str(self._assembly), mode,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, env=_environment(),
                cwd=str(self._assembly.parent), limit=16384))
            while True:
                try:
                    child = await asyncio.shield(launch)
                    break
                except asyncio.CancelledError:
                    if launch.cancelled():
                        raise DataStopped() from None
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError()
            child.stdin.write(_input_frame(request))
            await bounded(child.stdin.drain())
            child.stdin.close()  # one input frame + EOF, no later input accepted
            callback = await _read_target(child.stdout, bounded)
            if await bounded(child.wait()) != 0:
                raise DataStopped()
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            failed = True
        finally:
            if child is not None:
                try:
                    cleanup_failed, again = await _join_cleanup(asyncio.create_task(_reap(child)))
                    cancelled |= again
                    failed |= cleanup_failed
                except Exception:
                    failed = True
            if cancelled or failed or time.monotonic() >= deadline:
                attempt.cancel()
                if cancelled:
                    raise asyncio.CancelledError() from None
                raise DataStopped() from None
        # Commit only AFTER EOF, zero exit, verified cleanup and deadline checks.
        # A valid denial consumes the attempt too; neither outcome prints data.
        try:
            result = attempt.consume_callback(callback)
            if time.monotonic() >= deadline:
                raise DataStopped()
            return result
        except Exception:
            attempt.cancel()
            raise DataStopped() from None
