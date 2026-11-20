"""Offline cancellation probes. No real sockets, keys or provider data."""
import asyncio
import gc
import unittest

import httpx
from admin_http import AdminAISHTTP, AdminStopped
from provider_http import ReadOnlyHTTP
from provider_pager import FetchStopped, ReadRequest, HOST

ACCOUNT = '22222222-2222-4222-8222-222222222222'
SESSION = '11111111-1111-4111-8111-111111111111'


class CleanupStream(httpx.AsyncByteStream):
    def __init__(self, mode):
        self.mode = mode
        self.started = asyncio.Event()
        self.closing = asyncio.Event()
        self.release = asyncio.Event()
        self.closed = 0

    async def __aiter__(self):
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            if self.mode != 'suppressed':
                raise
        yield b'{}'

    async def aclose(self):
        self.closed += 1
        self.closing.set()
        if self.mode == 'repeated':
            await self.release.wait()
        if self.mode != 'suppressed':
            raise OSError('SYNTHETIC-CLEANUP-FAILURE')


class CancellationCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, route, mode='failed', timeout=False):
        stream = CleanupStream(mode)
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, headers={'content-type': 'application/json'}, stream=stream)
        transport = httpx.MockTransport(handler)
        seconds = .02 if timeout else 5
        if route == 'read':
            client = ReadOnlyHTTP(lambda: 'a.b.c', accounts=frozenset([ACCOUNT]),
                                  session=SESSION, total_seconds=seconds, _test_transport=transport)
            coro = client(ReadRequest(HOST, '/accounts/' + ACCOUNT + '/balances', ()))
            expected = FetchStopped
        else:
            client = AdminAISHTTP(lambda: 'a.b.c', total_seconds=seconds, _test_transport=transport)
            coro = client.exchange_code({'code': 'synthetic'})
            expected = AdminStopped
        loop = asyncio.get_running_loop()
        diagnostics = []
        previous = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: diagnostics.append(context))
        task = asyncio.create_task(coro)
        try:
            await asyncio.wait_for(stream.started.wait(), 1)
            if not timeout:
                task.cancel()
            if mode == 'repeated':
                await asyncio.wait_for(stream.closing.wait(), 1)
                task.cancel()
                stream.release.set()
            with self.assertRaises(expected if timeout else asyncio.CancelledError) as raised:
                await task
            if timeout and route == 'read':
                self.assertEqual(str(raised.exception), 'time_budget')
            self.assertEqual(task.cancelled(), not timeout)
            self.assertEqual(len(calls), 1)
            self.assertEqual(stream.closed, 1)
            del task
            gc.collect()
            await asyncio.sleep(0)
            self.assertEqual(diagnostics, [])
        finally:
            stream.release.set()
            loop.set_exception_handler(previous)

    async def test_read_cancellation_cleanup_error(self):
        await self.probe('read')

    async def test_admin_cancellation_cleanup_error(self):
        await self.probe('admin')

    async def test_read_timeout_cleanup_error(self):
        await self.probe('read', timeout=True)

    async def test_admin_timeout_cleanup_error(self):
        await self.probe('admin', timeout=True)

    async def test_read_cancellation_suppressed_success_rejected(self):
        await self.probe('read', mode='suppressed')

    async def test_admin_cancellation_suppressed_success_rejected(self):
        await self.probe('admin', mode='suppressed')

    async def test_read_repeated_cancellation(self):
        await self.probe('read', mode='repeated')

    async def test_admin_repeated_cancellation(self):
        await self.probe('admin', mode='repeated')
