"""Offline queue cancellation and generic-awaitable regressions."""
import asyncio
import gc
import unittest
from provider_load import SerialQueue, CallBudget, LoadStopped


class QueueCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, *, timeout=False, suppress=False):
        q = SerialQueue(interval=0)
        budget = CallBudget(calls=1, seconds=.02 if timeout else 5)
        entered = asyncio.Event()
        calls = []
        loop = asyncio.get_running_loop()
        diagnostics = []
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: diagnostics.append(context))
        async def operation():
            calls.append(1)
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if suppress:
                    return 'late-success'
                raise
            finally:
                if not suppress:
                    raise OSError('SYNTHETIC-QUEUE-CLEANUP-CANARY')
        task = asyncio.create_task(q.run(operation, budget))
        try:
            await asyncio.wait_for(entered.wait(), 1)
            if not timeout:
                task.cancel()
            with self.assertRaises(LoadStopped if timeout else asyncio.CancelledError):
                await task
            self.assertEqual(task.cancelled(), not timeout)
            self.assertEqual(calls, [1])
            self.assertEqual(q._pending, 0)
            self.assertFalse(q._lock.locked())
            with self.assertRaises(LoadStopped):
                budget.reserve()
            del task
            gc.collect()
            await asyncio.sleep(0)
            self.assertEqual(diagnostics, [])
            async def good():
                return 7
            self.assertEqual(await q.run(good, CallBudget(calls=1, seconds=5)), 7)
        finally:
            loop.set_exception_handler(previous)

    async def test_cancel_cleanup_error(self):
        await self.probe()

    async def test_timeout_cleanup_error(self):
        await self.probe(timeout=True)

    async def test_cancel_suppressed_success_rejected(self):
        await self.probe(suppress=True)

    async def test_timeout_suppressed_success_rejected(self):
        await self.probe(timeout=True, suppress=True)

    async def test_existing_future_supported(self):
        future = asyncio.get_running_loop().create_future()
        future.set_result(17)
        self.assertEqual(await SerialQueue(interval=0).run(lambda: future, CallBudget(calls=1, seconds=5)), 17)

    async def test_custom_awaitable_supported(self):
        class Custom:
            def __await__(self):
                async def value():
                    return 19
                return value().__await__()
        self.assertEqual(await SerialQueue(interval=0).run(Custom, CallBudget(calls=1, seconds=5)), 19)
