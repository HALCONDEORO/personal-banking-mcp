# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Synthetic duplex callback/ACK proof. No bank, listener, TLS host or store.

Unlike the one-way data fixture, the attempt is consumed BEFORE child exit.
A failure after consumption is not rollback, and never authorizes a retry.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import struct
from time import monotonic as _clock
from urllib.parse import urlencode

from admin_consent import ConsentAttempt
from callback_framing import ORIGIN, response_bytes
from relay_process import _environment, _join_cleanup, _reap, _seconds


class AckStopped(ValueError):
    def __init__(self):
        super().__init__('Private callback acknowledgement stopped')


@dataclass(frozen=True, repr=False)
class SyntheticAckReceipt:
    callback_validated: bool
    synthetic_browser_response: bytes

    def __repr__(self):
        return '<SyntheticAckReceipt synthetic-only; bank session not confirmed>'


_MODES = frozenset({'complete', 'early', 'bad-magic', 'oversize', 'truncated',
                    'bad-ascii', 'wrong-state', 'hold-before-data', 'hold-after-ack',
                    'nonzero', 'trailing', 'wrong-reply', 'denied', 'encoded', 'wrong-host'})


def _request_frame(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= 12288:
        raise AckStopped()
    return b'PAI1' + struct.pack('!I', len(raw)) + raw


def _ack_frame(accepted):
    if type(accepted) is not bool:
        raise AckStopped()
    return b'PAA1' + bytes([int(accepted)])


async def _read_frame(reader, magic, maximum, bounded):
    header = await bounded(reader.readexactly(8))
    size = struct.unpack('!I', header[4:])[0]
    if header[:4] != magic or not 1 <= size <= maximum:
        raise AckStopped()
    return await bounded(reader.readexactly(size))


class SyntheticAckRunner:
    """One use, fixed child and fresh invented attempt. Never a real callback API.

    A receipt describes fixed synthetic response bytes, NOT delivery to a browser
    and NOT a provider session. No auth code/session result is returned. A child
    that exits badly after ACK can already have received it: errors/cancellation
    withhold the receipt, but cannot retract sent bytes or unconsume the attempt.
    """
    __slots__ = ('_runtime', '_assembly', '_timeout', '_mode', '_used')

    def __init__(self, runtime, *, timeout=5, _mode='complete'):
        try:
            runtime = Path(runtime)
            if not runtime.is_absolute() or not runtime.is_file() or _mode not in _MODES:
                raise ValueError
            self._assembly = Path(__file__).resolve().parent / 'AckFixture' / 'bin' / 'Release' / 'net10.0' / 'AckFixture.dll'
            if not self._assembly.is_file():
                raise ValueError
            self._runtime, self._timeout = str(runtime.resolve()), _seconds(timeout)
            self._mode, self._used = _mode, False
        except Exception:
            raise AckStopped() from None

    def __repr__(self):
        return '<SyntheticAckRunner private>'

    async def __call__(self):
        if self._used:
            raise AckStopped()
        self._used = True
        deadline = _clock() + self._timeout
        attempt = ConsentAttempt(ORIGIN + '/callback')
        child = None
        cancelled = failed = False
        receipt = None

        async def bounded(awaitable):
            remaining = deadline - _clock()
            if remaining <= 0:
                awaitable.close()
                raise AckStopped()
            value = await asyncio.wait_for(awaitable, remaining)
            if _clock() >= deadline:
                raise AckStopped()
            return value

        try:
            auth = attempt.authorization_body('Synthetic fixture only', 'IE', now=datetime.now(timezone.utc))
            query = {'state': auth['state']}
            query.update({'error': 'synthetic-denied'} if self._mode == 'denied'
                         else {'code': 'synthetic+/%code' if self._mode == 'encoded' else 'synthetic-private-code'})
            host = 'evil.invalid' if self._mode == 'wrong-host' else 'localhost:8765'
            raw = ('GET /callback?' + urlencode(query) + ' HTTP/1.1\r\nHost: ' + host + '\r\n\r\n').encode('ascii')
            mode = 'complete' if self._mode in {'denied', 'encoded', 'wrong-host'} else self._mode
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
                        raise AckStopped() from None
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError()
            child.stdin.write(_request_frame(raw))
            await bounded(child.stdin.drain())
            # Input stays open for exactly one ACK. EOF here would deadlock the protocol.
            target = (await _read_frame(child.stdout, b'PAD1', 8192-len(ORIGIN), bounded)).decode('ascii')
            if not target.startswith('/callback?') or any(ord(c) < 33 or ord(c) > 126 for c in target):
                raise AckStopped()
            if _clock() >= deadline:
                raise AckStopped()
            accepted = False
            # The trusted synthetic child is still alive. No exit-before-consume claim.
            try:
                attempt.consume_callback(ORIGIN + target)
                accepted = True
            except Exception:
                attempt.cancel()
            if _clock() >= deadline:
                raise AckStopped()
            child.stdin.write(_ack_frame(accepted))
            await bounded(child.stdin.drain())
            child.stdin.close()  # exact ACK followed by EOF
            response = await _read_frame(child.stdout, b'PAR1', 1024, bounded)
            if response != response_bytes(accepted=accepted):
                raise AckStopped()
            if await bounded(child.stdout.read(1)) != b'' or await bounded(child.wait()) != 0:
                raise AckStopped()
            receipt = SyntheticAckReceipt(accepted, response)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            failed = True
        finally:
            attempt.cancel()  # consume/cancel always final; never resurrect on ACK failure
            if child is not None:
                try:
                    cleanup_failed, again = await _join_cleanup(asyncio.create_task(_reap(child)))
                    cancelled |= again
                    failed |= cleanup_failed
                except Exception:
                    failed = True
            if cancelled:
                raise asyncio.CancelledError() from None
            if failed or receipt is None or _clock() >= deadline:
                raise AckStopped() from None
        return receipt
