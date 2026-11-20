# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from admin_consent import ConsentAttempt
from callback_framing import relay_request
from callback_receiver import CallbackReceiver
from relay_supervisor import run_local_attempt, LocalAttemptStopped


class SupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.attempt = ConsentAttempt('https://localhost:8765/callback')
        body = self.attempt.authorization_body('Synthetic bank', 'IE', now=datetime.now(timezone.utc))
        self.target = '/callback?' + urlencode({'state': body['state'], 'code': 'SYNTHETIC-CODE'})
        self.receiver = CallbackReceiver(self.attempt, port=0, lifetime_seconds=1)
        self.port = None

    async def asyncTearDown(self):
        await self.receiver.close()

    async def assert_closed(self):
        self.assertTrue(self.attempt.closed)
        self.assertIsNone(self.receiver._server)
        self.assertFalse(self.receiver._tasks)
        if self.port:
            with self.assertRaises(OSError):
                await asyncio.open_connection('127.0.0.1', self.port)

    async def send(self, target):
        self.port = self.receiver.port
        reader, writer = await asyncio.open_connection('127.0.0.1', self.port)
        writer.write(relay_request(target))
        await writer.drain()
        writer.write_eof()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        return response

    async def test_success(self):
        async def relay():
            response = await self.send(self.target)
            self.assertIn(b'200 OK', response)
        result = await run_local_attempt(self.receiver, relay)
        self.assertEqual(result, {'code': 'SYNTHETIC-CODE'})
        await self.assert_closed()

    async def test_denial(self):
        async def relay():
            await self.send(self.target.replace('code=SYNTHETIC-CODE', 'error=denied'))
        with self.assertRaises(LocalAttemptStopped):
            await run_local_attempt(self.receiver, relay)
        await self.assert_closed()

    async def test_relay_failure_before_connect(self):
        async def relay():
            self.port = self.receiver.port
            raise ValueError('synthetic private failure must not escape')
        with self.assertRaisesRegex(LocalAttemptStopped, '^Local attempt stopped$'):
            await run_local_attempt(self.receiver, relay)
        await self.assert_closed()

    async def test_clean_exit_without_callback(self):
        async def relay():
            self.port = self.receiver.port
        with self.assertRaises(LocalAttemptStopped):
            await run_local_attempt(self.receiver, relay)
        await self.assert_closed()

    async def test_cancellation(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()
        async def relay():
            self.port = self.receiver.port
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()
        task = asyncio.create_task(run_local_attempt(self.receiver, relay))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(cancelled.is_set())
        await self.assert_closed()

    async def test_success_but_relay_does_not_exit(self):
        cancelled = asyncio.Event()
        async def relay():
            try:
                await self.send(self.target)
                await asyncio.Future()
            finally:
                cancelled.set()
        with self.assertRaises(LocalAttemptStopped):
            await run_local_attempt(self.receiver, relay)
        self.assertTrue(cancelled.is_set())
        await self.assert_closed()

    async def test_start_bind_failure(self):
        server = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        self.receiver = CallbackReceiver(self.attempt, port=server.sockets[0].getsockname()[1])
        called = False
        async def relay():
            nonlocal called
            called = True
        try:
            with self.assertRaises(LocalAttemptStopped):
                await run_local_attempt(self.receiver, relay)
            self.assertFalse(called)
            await self.assert_closed()
        finally:
            server.close()
            await server.wait_closed()


class FaultedCloseTests(unittest.IsolatedAsyncioTestCase):
    class Receiver:
        def __init__(self, *, block_close=False, fail_close=False):
            self.started = asyncio.Event()
            self.waiter_started = asyncio.Event()
            self.closing = asyncio.Event()
            self.release_close = asyncio.Event()
            self.block_close = block_close
            self.fail_close = fail_close
            self.closed = False
            self.waiter = None
            self.waiter_cancelled = False

        async def start(self):
            self.started.set()

        async def wait_private_result(self):
            self.waiter = asyncio.current_task()
            self.waiter_started.set()
            try:
                await asyncio.Future()
            finally:
                self.waiter_cancelled = True

        async def close(self):
            self.closing.set()
            if self.block_close:
                await self.release_close.wait()
            if self.fail_close:
                raise OSError('synthetic close failure, not safe to echo')
            self.closed = True

    async def exercise(self, *, cancel_first, cancel_during, close_fails):
        receiver = self.Receiver(block_close=cancel_during, fail_close=close_fails)
        relay_started = asyncio.Event()
        relay_cancelled = asyncio.Event()
        relay_exit = asyncio.Event()
        owned = []
        async def relay():
            owned.append(asyncio.current_task())
            relay_started.set()
            try:
                await relay_exit.wait()
            finally:
                relay_cancelled.set()
        task = asyncio.create_task(run_local_attempt(receiver, relay))
        await asyncio.wait_for(relay_started.wait(), 1)
        await asyncio.wait_for(receiver.waiter_started.wait(), 1)
        if cancel_first:
            task.cancel()
        else:
            relay_exit.set()
        await asyncio.wait_for(receiver.closing.wait(), 1)
        if cancel_during:
            task.cancel()
            # Give the cancellation a turn while close is still blocked.
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            receiver.release_close.set()
        if cancel_first or cancel_during:
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
        else:
            with self.assertRaisesRegex(LocalAttemptStopped, '^Local attempt stopped$'):
                await asyncio.wait_for(task, 1)
        self.assertTrue(receiver.waiter.done())
        self.assertTrue(receiver.waiter_cancelled)
        self.assertTrue(all(t.done() for t in owned))
        self.assertTrue(relay_cancelled.is_set())
        # Failure does NOT establish listener closure. The fake reports unknown.
        self.assertEqual(receiver.closed, not close_fails)

    async def test_close_error_still_joins_both_tasks(self):
        await self.exercise(cancel_first=False, cancel_during=False, close_fails=True)

    async def test_cancel_then_close_error_preserves_cancellation(self):
        await self.exercise(cancel_first=True, cancel_during=False, close_fails=True)

    async def test_additional_cancellation_during_close(self):
        await self.exercise(cancel_first=True, cancel_during=True, close_fails=False)

    async def test_additional_cancellation_and_close_error(self):
        await self.exercise(cancel_first=True, cancel_during=True, close_fails=True)

    async def test_first_cancellation_arrives_during_close(self):
        await self.exercise(cancel_first=False, cancel_during=True, close_fails=False)


if __name__ == '__main__':
    unittest.main()
