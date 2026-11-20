"""Synthetic cancellation regressions for pager and checked-session composition."""
import asyncio
import gc
import json
import unittest
from datetime import datetime, timedelta, timezone
from provider_pager import (FakeResponse, FetchStopped, HOST, ReadRequest,
                            Limits, fetch_simulated_transactions)
from provider_checked_session import CheckedSessionRead, SessionReadStopped
from provider_session import PrivateSession

SID = '11111111-1111-4111-8111-111111111111'
AID = '22222222-2222-4222-8222-222222222222'
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


class ReadCompositionCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, *, checked, account_phase=False, timeout=False, suppress=False):
        entered = asyncio.Event()
        calls = []
        diagnostics = []
        loop = asyncio.get_running_loop()
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: diagnostics.append(context))

        async def transport(request):
            calls.append(request.path)
            if checked and account_phase and len(calls) == 1:
                payload = {'status': 'AUTHORIZED', 'psu_type': 'personal',
                           'aspsp': {'name': 'Synthetic bank', 'country': 'IE'},
                           'access': {'valid_until': (NOW + timedelta(hours=1)).isoformat()},
                           'accounts': [AID]}
                return FakeResponse(200, json.dumps(payload).encode())
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if suppress:
                    return FakeResponse(200, b'{"transactions":[]}')
                raise
            finally:
                if not suppress:
                    raise OSError('SYNTHETIC-READ-CLEANUP-CANARY')

        if checked:
            reader = CheckedSessionRead(
                session=PrivateSession(SID, (AID,), NOW + timedelta(hours=2)),
                bank='Synthetic bank', country='IE', transport=transport, now=lambda: NOW,
                seconds=.05 if timeout else 5)
            operation = reader(ReadRequest(HOST, '/accounts/' + AID + '/balances', ()))
        else:
            operation = fetch_simulated_transactions(
                AID, frozenset([AID]), '2026-11-01', '2026-11-20', transport,
                limits=Limits(seconds=.05 if timeout else 5))
        task = asyncio.create_task(operation)
        try:
            await asyncio.wait_for(entered.wait(), 1)
            if not timeout:
                task.cancel()
            expected = (SessionReadStopped if checked else FetchStopped) if timeout else asyncio.CancelledError
            with self.assertRaises(expected):
                await task
            self.assertEqual(task.cancelled(), not timeout)
            self.assertEqual(len(calls), 2 if account_phase else 1)
            del task
            gc.collect()
            await asyncio.sleep(0)
            self.assertEqual(diagnostics, [])
            if checked:
                self.assertFalse(reader._lock.locked())
                async def refused(request):
                    return FakeResponse(403, b'')
                reader._transport = refused
                with self.assertRaises(SessionReadStopped):
                    await reader(ReadRequest(HOST, '/accounts/' + AID + '/balances', ()))
        finally:
            loop.set_exception_handler(previous)
            if 'task' in locals() and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def test_pager_caller_cancellation_survives_cleanup_error(self):
        await self.probe(checked=False)

    async def test_session_check_cancellation_survives_cleanup_error(self):
        await self.probe(checked=True)

    async def test_account_read_cancellation_survives_cleanup_error(self):
        await self.probe(checked=True, account_phase=True)


    async def test_pager_timeout_cleanup_error(self):
        await self.probe(checked=False, timeout=True)

    async def test_session_timeout_cleanup_error(self):
        await self.probe(checked=True, timeout=True)

    async def test_account_timeout_cleanup_error(self):
        await self.probe(checked=True, account_phase=True, timeout=True)

    async def test_pager_suppressed_cancel_success_refused(self):
        await self.probe(checked=False, suppress=True)

    async def test_session_suppressed_cancel_success_refused(self):
        await self.probe(checked=True, suppress=True)

    async def test_pager_suppressed_timeout_success_refused(self):
        await self.probe(checked=False, timeout=True, suppress=True)

    async def test_session_suppressed_timeout_success_refused(self):
        await self.probe(checked=True, timeout=True, suppress=True)


if __name__ == '__main__':
    unittest.main()
