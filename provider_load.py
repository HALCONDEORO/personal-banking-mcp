# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
# Adapted queue pattern: HALCONDEORO/tesco-ie-grocery-mcp
# pin08db94c5230ab74d9a573415442e22a5961e5c69, src/load-control.mjs
# Changes: Python asyncio, bounded pending/count/deadline, monotonic checks,
# cancellation propagation and generic errors. No network wiring or retries.
"""Explicit internal scheduling primitive, not an MCP tool or rate policy."""
import asyncio
import inspect
import math
import time
from async_boundary import _await_owned


class LoadStopped(ValueError):
    def __init__(self):
        super().__init__('Local request budget stopped')


def _number(value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise LoadStopped()
    return float(value)


class CallBudget:
    """One workflow budget. One-use call slots are never refunded on errors.

    Cooperative only. A coroutine can delay cancellation and synchronous code
    can block the event loop. A hard process supervisor is a separate concern.
    """
    def __init__(self, *, calls, seconds, now=time.monotonic):
        if type(calls) is not int or not 1 <= calls <= 100 or not callable(now):
            raise LoadStopped()
        seconds = _number(seconds, 0.001, 300)
        self._now = now
        self._previous = self._read()
        self._deadline = self._previous + seconds
        self._calls = calls

    def __repr__(self):
        return '<CallBudget private>'

    def _read(self):
        failed = False
        try:
            value = self._now()
        except Exception:
            failed = True
        if failed:
            raise LoadStopped()
        return _number(value, -1e15, 1e15)

    def remaining(self):
        value = self._read()
        if value < self._previous:
            raise LoadStopped()
        self._previous = value
        left = self._deadline - value
        if left <= 0:
            raise LoadStopped()
        return left

    def reserve(self):
        self.remaining()
        if self._calls <= 0:
            raise LoadStopped()
        self._calls -= 1


class SerialQueue:
    """Per-instance, one-event-loop serial queue. Not process-global by magic.

    Caller must share one instance at the correct provider/account scope. The
    interval is an operator choice, not a verified bank/provider rate policy.
    No concurrent HTTP, retries, renewal, background worker or persistence.
    """
    def __init__(self, *, interval=2.0, max_pending=8, now=time.monotonic,
                 sleep=asyncio.sleep):
        self._interval = _number(interval, 0, 60)
        if type(max_pending) is not int or not 1 <= max_pending <= 64:
            raise LoadStopped()
        if not callable(now) or not callable(sleep):
            raise LoadStopped()
        self._cap = max_pending
        self._now = now
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._pending = 0
        self._last = None
        self._clock = None
        self._loop = None

    def __repr__(self):
        return '<SerialQueue private>'

    def _read(self):
        failed = False
        try:
            value = self._now()
        except Exception:
            failed = True
        if failed:
            raise LoadStopped()
        value = _number(value, -1e15, 1e15)
        if self._clock is not None and value < self._clock:
            raise LoadStopped()
        self._clock = value
        return value

    async def run(self, operation, budget):
        if not callable(operation) or type(budget) is not CallBudget:
            raise LoadStopped()
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise LoadStopped()
        self._loop = loop
        if self._pending >= self._cap:
            raise LoadStopped()
        budget.remaining()
        self._pending += 1
        acquired = False
        failed = False
        try:
            timeout = budget.remaining()
            await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            acquired = True
            now = self._read()
            delay = 0 if self._last is None else max(0, self._interval - (now-self._last))
            if delay:
                if delay >= budget.remaining():
                    raise LoadStopped()
                timeout = budget.remaining()
                await asyncio.wait_for(self._sleep(delay), timeout=timeout)
                now = self._read()
                if now-self._last < self._interval:
                    raise LoadStopped()
            budget.reserve()
            self._last = now
            # Coroutine function invocation itself must remain nonblocking.
            # No arbitrary synchronous callback can be forcibly timed out.
            timeout = budget.remaining()
            result = operation()
            if not inspect.isawaitable(result):
                raise LoadStopped()
            value = await _await_owned(result, timeout)
            budget.remaining()
            return value
        except asyncio.CancelledError:
            raise
        except Exception:
            failed = True
        finally:
            if acquired:
                self._lock.release()
            self._pending -= 1
        if failed:
            raise LoadStopped()
