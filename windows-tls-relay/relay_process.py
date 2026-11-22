# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Private control-pipe prototype, synthetic child only. No relay/bank/store.

The fixed child assembly has no production entry point. This module supplies no
arbitrary command, shell, certificate selection, token or callback transport.
The runtime and repository/build directory must be trusted local configuration.
Only the direct child is contained; descendants/hostile same-user code are not.
"""
import asyncio
import math
import os
from pathlib import Path
import time


class ControlStopped(ValueError):
    def __init__(self):
        super().__init__('Private control stopped')


def _seconds(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 30:
        raise ControlStopped()
    return float(value)


def _environment():
    # Do not inherit loader/startup hooks or application secrets into the child.
    keep = {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE', 'APPDATA',
            'LOCALAPPDATA', 'HOME', 'DOTNET_ROOT'}
    result = {k: v for k, v in os.environ.items() if k.upper() in keep}
    result.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_NOLOGO='1',
                  DOTNET_GENERATE_ASPNET_CERTIFICATE='false')
    return result


async def _reap(child):
    """Best-effort stop escalation, always await the direct child after kill.

    wait() after kill deliberately has no fabricated hard upper bound. Kernel or
    process API failures are errors, never a claim of successful containment.
    """
    failed = False
    async def discard_output():
        try:
            while await child.stdout.read(4096):
                pass
            return False
        except Exception:
            return True
    # Keep a full output pipe from blocking Process.wait during stop escalation.
    drain = (asyncio.create_task(discard_output())
             if getattr(child, 'stdout', None) is not None else None)
    if child.stdin is not None:
        try:
            if child.returncode is None:
                child.stdin.write(b'STOP 1\n')
                await asyncio.wait_for(child.stdin.drain(), .25)
        except Exception:
            pass  # Broken input is expected if the child has already exited.
        finally:
            try:
                child.stdin.close()
            except Exception:
                failed = True
    try:
        await asyncio.wait_for(child.wait(), .25)
    except Exception as error:
        failed |= not isinstance(error, asyncio.TimeoutError)
        # A wait API error must not bypass stop escalation either.
        try:
            child.terminate()
        except ProcessLookupError:
            pass
        except Exception:
            failed = True
        try:
            await asyncio.wait_for(child.wait(), .25)
        except Exception as error:
            failed |= not isinstance(error, asyncio.TimeoutError)
            try:
                child.kill()
            except ProcessLookupError:
                pass
            except Exception:
                failed = True
            try:
                await child.wait()
            except Exception:
                failed = True
    if child.returncode is None:
        failed = True
    if drain is not None:
        if not drain.done():
            drain.cancel()
        result = await asyncio.gather(drain, return_exceptions=True)
        if result[0] is True:
            failed = True
    return failed


async def _join_cleanup(task):
    cancelled = False
    while True:
        try:
            return await asyncio.shield(task), cancelled
        except asyncio.CancelledError:
            if task.cancelled():
                raise ControlStopped() from None
            cancelled = True


class SyntheticControlRunner:
    """One-use, fixed-assembly synthetic runner. Callable for run_local_attempt.

    No production relay is launched. timeout includes startup and protocol work,
    but cleanup can exceed it. No secret is accepted or returned. Unexpected
    output, extra frames, nonzero exit or elapsed deadline are failures.
    """
    __slots__ = ('_runtime', '_assembly', '_timeout', '_used', '_mode')

    def __init__(self, runtime, *, timeout=5, _mode='complete'):
        try:
            runtime = Path(runtime)
            if not runtime.is_absolute() or not runtime.is_file():
                raise ValueError
            if _mode not in {'complete', 'hold', 'early', 'extra', 'flood', 'reject-stop'}:
                raise ValueError
            self._assembly = Path(__file__).resolve().parent / 'ControlFixture' / 'bin' / 'Release' / 'net10.0' / 'ControlFixture.dll'
            if not self._assembly.is_file():
                raise ValueError
            self._runtime, self._timeout = str(runtime.resolve()), _seconds(timeout)
            self._mode, self._used = _mode, False
        except Exception:
            raise ControlStopped() from None

    def __repr__(self):
        return '<SyntheticControlRunner private>'

    async def __call__(self):
        if self._used:
            raise ControlStopped()
        self._used = True
        deadline = time.monotonic() + self._timeout
        child = None
        cancelled = False
        failed = False

        async def bounded(awaitable):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                awaitable.close()
                raise ControlStopped()
            result = await asyncio.wait_for(awaitable, remaining)
            if time.monotonic() >= deadline:
                raise ControlStopped()
            return result

        try:
            # Shield acquisition: cancellation must not lose a successfully spawned child.
            launch = asyncio.create_task(asyncio.create_subprocess_exec(
                self._runtime, str(self._assembly), self._mode,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, env=_environment(),
                cwd=str(self._assembly.parent), limit=128))
            while True:
                try:
                    child = await asyncio.shield(launch)
                    break
                except asyncio.CancelledError:
                    if launch.cancelled():
                        raise ControlStopped() from None
                    cancelled = True
            if cancelled:
                raise asyncio.CancelledError()
            child.stdin.write(b'START 1\n')
            await bounded(child.stdin.drain())
            if await bounded(child.stdout.readline()) != b'READY 1\n':
                raise ControlStopped()
            if await bounded(child.stdout.readline()) != b'DONE 1\n':
                raise ControlStopped()
            # Any trailing byte is forbidden, even after a valid DONE frame.
            if await bounded(child.stdout.read(1)) != b'':
                raise ControlStopped()
            if await bounded(child.wait()) != 0:
                raise ControlStopped()
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            failed = True
        finally:
            if child is not None:
                cleanup = asyncio.create_task(_reap(child))
                try:
                    cleanup_failed, again = await _join_cleanup(cleanup)
                    cancelled |= again
                    failed |= cleanup_failed
                except Exception:
                    failed = True
            if cancelled:
                raise asyncio.CancelledError() from None
            if failed:
                raise ControlStopped() from None
