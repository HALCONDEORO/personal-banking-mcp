"""Synthetic early timer cancellation, not a Windows or real bank simulation."""
import asyncio
import json
import unittest
from datetime import timedelta
from unittest.mock import patch
from provider_doctor import run_doctor, ProbeResult
from provider_checked_session import CheckedSessionRead, SessionReadStopped
from provider_session import PrivateSession
from provider_pager import FakeResponse, HOST, ReadRequest
from test_provider_checked_session import SID, AID, NOW, payload


class EarlyTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # A ready task lets the event loop dispatch timers inside its clock
        # resolution window, before loop.time() reaches their nominal deadline.
        async def keep_ready():
            while True:
                await asyncio.sleep(0)
        self.ready = asyncio.create_task(keep_ready())

    async def asyncTearDown(self):
        self.ready.cancel()
        await asyncio.gather(self.ready, return_exceptions=True)

    async def test_doctor_timeout_not_reachable_when_cleanup_suppresses_cancel(self):
        calls = []
        async def probe():
            calls.append(1)
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return ProbeResult(200)
        loop = asyncio.get_running_loop()
        with patch.object(loop, '_clock_resolution', 1):
            result = await run_doctor(probe, seconds=.1)
        self.assertEqual(result['status'], 'timeout')
        self.assertEqual(calls, [1])

    async def test_session_timeout_does_not_start_account_read(self):
        calls = []
        async def transport(request):
            calls.append(request.path)
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                return FakeResponse(200, json.dumps(payload()).encode())
        reader = CheckedSessionRead(
            session=PrivateSession(SID, (AID,), NOW + timedelta(hours=2)),
            bank='Synthetic bank', country='IE', transport=transport,
            now=lambda: NOW, seconds=.1)
        loop = asyncio.get_running_loop()
        with patch.object(loop, '_clock_resolution', 1):
            with self.assertRaises(SessionReadStopped):
                await reader(ReadRequest(HOST, '/accounts/' + AID + '/balances', ()))
        self.assertEqual(calls, ['/sessions/' + SID])
        self.assertFalse(reader._lock.locked())


if __name__ == '__main__':
    unittest.main()
