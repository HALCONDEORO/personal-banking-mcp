# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Native synthetic processes, real .NET parser and real Python consent logic."""
import asyncio
import contextlib
import io
import os
from pathlib import Path
import struct
import sys
import traceback
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from admin_consent import ConsentAttempt, SetupRejected
from callback_pipe import DataStopped, SyntheticDataRunner, _input_frame, _read_target
from relay_process import _environment, _reap


class DataTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = os.environ['CONTROL_TEST_DOTNET']
        self.children = []
        self.attempts = []
        self.real_spawn = asyncio.create_subprocess_exec

    def attempt(self, *args, **kwargs):
        result = ConsentAttempt(*args, **kwargs)
        self.attempts.append(result)
        return result

    async def spawn(self, *args, **kwargs):
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['stderr'], asyncio.subprocess.DEVNULL)
        self.assertEqual(len(args), 3)
        self.assertTrue(Path(args[0]).is_absolute())
        self.assertEqual(Path(args[1]).name, 'DataFixture.dll')
        for value in args:
            self.assertNotIn('synthetic-private-code', value)
            self.assertNotIn('state=', value)
        for key in ('DOTNET_STARTUP_HOOKS', 'BANK_TOKEN', 'LD_PRELOAD'):
            self.assertNotIn(key, kwargs['env'])
        child = await self.real_spawn(*args, **kwargs)
        original = child.stdout
        child.data_ready = False
        class ObserveReader:
            async def readexactly(self, size):
                result = await original.readexactly(size)
                if size != 8:
                    child.data_ready = True
                return result
            async def read(self, size):
                return await original.read(size)
        child.stdout = ObserveReader()
        self.children.append(child)
        return child

    def runner(self, mode='complete', timeout=3):
        return SyntheticDataRunner(self.runtime, _mode=mode, timeout=timeout)

    async def run_mode(self, mode='complete', timeout=3):
        with patch('asyncio.create_subprocess_exec', self.spawn), patch('callback_pipe.ConsentAttempt', self.attempt):
            return await self.runner(mode, timeout)()

    async def asyncTearDown(self):
        for child in self.children:
            self.assertIsNotNone(child.returncode, 'direct child was not reaped')
            self.assertTrue(child.stdin.is_closing())
        for attempt in self.attempts:
            self.assertTrue(attempt.closed, 'attempt was neither consumed nor cancelled')

    async def test_real_parser_and_consent_success(self):
        self.assertEqual(await self.run_mode(), {'code': 'synthetic-private-code'})
        self.assertEqual(self.children[0].returncode, 0)

    async def test_actual_cross_language_percent_encoding(self):
        self.assertEqual(await self.run_mode('encoded'), {'code': 'synthetic+/%code'})

    async def test_one_use_and_no_second_spawn(self):
        runner = self.runner()
        with patch('asyncio.create_subprocess_exec', self.spawn), patch('callback_pipe.ConsentAttempt', self.attempt):
            await runner()
            with self.assertRaises(DataStopped):
                await runner()
        self.assertEqual(len(self.children), 1)

    async def test_consumes_only_after_exit_and_cleanup(self):
        consume = ConsentAttempt.consume_callback
        calls = []
        def checked(attempt, callback):
            self.assertEqual(len(self.children), 1)
            self.assertEqual(self.children[0].returncode, 0)
            self.assertTrue(self.children[0].stdin.is_closing())
            calls.append(True)
            result = consume(attempt, callback)
            with self.assertRaises(SetupRejected):
                consume(attempt, callback)  # real replay rejected
            return result
        with patch.object(ConsentAttempt, 'consume_callback', checked):
            await self.run_mode()
        self.assertEqual(calls, [True])

    async def test_denial_consumes_without_result(self):
        consume = ConsentAttempt.consume_callback
        calls = []
        def checked(attempt, callback):
            try:
                return consume(attempt, callback)
            finally:
                calls.append(attempt.closed)
        with patch.object(ConsentAttempt, 'consume_callback', checked):
            with self.assertRaisesRegex(DataStopped, '^Private callback stopped$'):
                await self.run_mode('denied')
        self.assertEqual(calls, [True])

    async def test_wrong_state_is_generic(self):
        with self.assertRaisesRegex(DataStopped, '^Private callback stopped$'):
            await self.run_mode('wrong-state')

    async def test_real_dotnet_parser_rejects_wrong_host(self):
        with self.assertRaises(DataStopped):
            await self.run_mode('wrong-host')
        self.assertNotEqual(self.children[0].returncode, 0)

    async def rejected_before_consume(self, mode):
        with patch.object(ConsentAttempt, 'consume_callback', side_effect=AssertionError('must not consume')) as consume:
            with self.assertRaises(DataStopped):
                await self.run_mode(mode)
            consume.assert_not_called()

    async def test_bad_magic_not_consumed(self):
        await self.rejected_before_consume('bad-magic')

    async def test_oversize_not_consumed(self):
        await self.rejected_before_consume('oversize')

    async def test_truncated_not_consumed(self):
        await self.rejected_before_consume('truncated')

    async def test_duplicate_not_consumed(self):
        await self.rejected_before_consume('duplicate')

    async def test_trailing_not_consumed(self):
        await self.rejected_before_consume('trailing')

    async def test_nonzero_after_valid_frame_not_consumed(self):
        await self.rejected_before_consume('nonzero')

    async def test_early_exit_not_consumed(self):
        await self.rejected_before_consume('early')

    async def test_output_flood_not_consumed_and_reaped(self):
        await self.rejected_before_consume('flood')

    async def test_non_ascii_not_consumed(self):
        await self.rejected_before_consume('bad-ascii')

    async def test_valid_frame_without_eof_times_out_not_consumed(self):
        with patch.object(ConsentAttempt, 'consume_callback') as consume:
            with self.assertRaises(DataStopped):
                await self.run_mode('hold', timeout=1)
            consume.assert_not_called()
        self.assertTrue(self.children[0].data_ready)

    async def test_repeated_cancel_after_data_waits_for_reap(self):
        with patch('asyncio.create_subprocess_exec', self.spawn), patch('callback_pipe.ConsentAttempt', self.attempt):
            task = asyncio.create_task(self.runner('hold')())
            while not self.children or not self.children[0].data_ready:
                if task.done():
                    await task
                    self.fail('child completed before data')
                await asyncio.sleep(.001)
            task.cancel()
            await asyncio.sleep(.01)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_cancel_during_spawn_does_not_lose_child(self):
        spawned, release = asyncio.Event(), asyncio.Event()
        async def delayed(*args, **kwargs):
            child = await self.spawn(*args, **kwargs)
            spawned.set()
            await release.wait()
            return child
        with patch('asyncio.create_subprocess_exec', delayed), patch('callback_pipe.ConsentAttempt', self.attempt):
            task = asyncio.create_task(self.runner()())
            await spawned.wait()
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_cancel_during_cleanup_cannot_commit_or_interrupt_reap(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed_cleanup(child):
            entered.set()
            await release.wait()
            return await _reap(child)
        with patch('callback_pipe._reap', delayed_cleanup), patch('asyncio.create_subprocess_exec', self.spawn):
            with patch('callback_pipe.ConsentAttempt', self.attempt), patch.object(ConsentAttempt, 'consume_callback') as consume:
                task = asyncio.create_task(self.runner()())
                await entered.wait()
                task.cancel()
                await asyncio.sleep(0)
                task.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                consume.assert_not_called()

    async def test_unknown_cleanup_refuses_success(self):
        async def failed_cleanup(child):
            await _reap(child)
            return True
        with patch('callback_pipe._reap', failed_cleanup), patch.object(ConsentAttempt, 'consume_callback') as consume:
            with self.assertRaises(DataStopped):
                await self.run_mode()
            consume.assert_not_called()

    async def test_spawn_failure_generic_and_attempt_cancelled(self):
        async def fail(*args, **kwargs):
            raise OSError('synthetic private diagnostic')
        with patch('asyncio.create_subprocess_exec', fail), patch('callback_pipe.ConsentAttempt', self.attempt):
            with self.assertRaisesRegex(DataStopped, '^Private callback stopped$'):
                await self.runner()()

    async def test_expiry_after_cleanup_not_consumed(self):
        offset = [0]
        import time
        clock = time.monotonic
        async def slow_cleanup(child):
            result = await _reap(child)
            offset[0] = 20
            return result
        with patch('callback_pipe._reap', slow_cleanup), patch('callback_pipe._clock', lambda: clock() + offset[0]):
            with patch.object(ConsentAttempt, 'consume_callback') as consume:
                with self.assertRaises(DataStopped):
                    await self.run_mode()
                consume.assert_not_called()

    async def test_public_error_traceback_and_output_value_free(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                await self.run_mode('nonzero')
            except DataStopped as error:
                text = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                self.assertNotIn('synthetic-private-code', text)
                self.assertNotIn('state=', text)
                self.assertIsNone(error.__cause__)
            else:
                self.fail('nonzero exit accepted')
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')
        self.assertEqual(repr(self.runner()), '<SyntheticDataRunner private>')

    async def test_configuration_rejected_without_spawn(self):
        for timeout in (0, -1, True, float('nan'), float('inf'), 31):
            with self.assertRaises(DataStopped):
                self.runner(timeout=timeout)
        with self.assertRaises(DataStopped):
            SyntheticDataRunner('relative-dotnet')
        with self.assertRaises(DataStopped):
            self.runner(mode='arbitrary-command')
        self.assertEqual(self.children, [])

    async def test_dotnet_rejects_malformed_input_frames(self):
        runner = self.runner()
        valid = b'GET /callback?state=x&code=y HTTP/1.1\r\nHost: localhost:8765\r\n\r\n'
        frame = _input_frame(valid)
        cases = [b'', b'PBI1', b'BAD!' + frame[4:], b'PBI1' + struct.pack('!I', 0),
                 b'PBI1' + struct.pack('!I', 0xffffffff), frame[:-1], frame + b'X', frame + frame]
        for value in cases:
            child = await self.spawn(self.runtime, str(runner._assembly), 'complete',
                                     stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                     stderr=asyncio.subprocess.DEVNULL, env=_environment())
            try:
                child.stdin.write(value)
                await child.stdin.drain()
                child.stdin.close()
                self.assertEqual(await asyncio.wait_for(child.stdout.read(1), 3), b'')
                self.assertNotEqual(await asyncio.wait_for(child.wait(), 3), 0)
            finally:
                await _reap(child)

    async def test_python_frame_reader_bounds_and_exact_eof(self):
        async def bounded(awaitable):
            return await awaitable
        for raw in (b'', b'PBD1', b'PBD1' + struct.pack('!I', 0),
                    b'PBD1' + struct.pack('!I', 0xffffffff),
                    b'PBD1' + struct.pack('!I', 8192),
                    b'PBD1' + struct.pack('!I', 2) + b'\xffX',
                    b'PBD1' + struct.pack('!I', 2) + b'/x'):
            reader = asyncio.StreamReader()
            reader.feed_data(raw)
            reader.feed_eof()
            with self.assertRaises((DataStopped, asyncio.IncompleteReadError, UnicodeError)):
                await _read_target(reader, bounded)

    async def test_input_frame_type_and_bounds(self):
        for value in ('text', None, bytearray(b'x'), b'', b'X' * 12289):
            with self.assertRaises(DataStopped):
                _input_frame(value)
        self.assertEqual(_input_frame(b'x'), b'PBI1\0\0\0\1x')


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DataTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun < 28:
        raise SystemExit(1)
