# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Real local subprocess checks, synthetic .NET child. Never accesses a bank."""
import asyncio
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from relay_process import SyntheticControlRunner, ControlStopped, _environment, _reap
from relay_supervisor import run_local_attempt


class ControlTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = os.environ['CONTROL_TEST_DOTNET']
        self.children = []
        self.real_spawn = asyncio.create_subprocess_exec

    async def spawn(self, *args, **kwargs):
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['stderr'], asyncio.subprocess.DEVNULL)
        self.assertNotIn('DOTNET_STARTUP_HOOKS', kwargs['env'])
        child = await self.real_spawn(*args, **kwargs)
        original = child.stdout
        child.control_ready = False
        class ObserveReader:
            async def readline(self):
                frame = await original.readline()
                if frame == b'READY 1\n':
                    child.control_ready = True
                return frame
            async def read(self, size):
                return await original.read(size)
        child.stdout = ObserveReader()
        self.children.append(child)
        return child

    def runner(self, mode='complete', timeout=2):
        return SyntheticControlRunner(self.runtime, _mode=mode, timeout=timeout)

    async def asyncTearDown(self):
        # A failure here is a real unreaped-child failure, not a skip.
        for child in self.children:
            self.assertIsNotNone(child.returncode)
            self.assertTrue(child.stdin.is_closing())

    async def test_complete_and_one_use(self):
        runner = self.runner()
        with patch('asyncio.create_subprocess_exec', self.spawn):
            self.assertIsNone(await runner())
            with self.assertRaises(ControlStopped):
                await runner()
        self.assertEqual(len(self.children), 1)
        self.assertEqual(self.children[0].returncode, 0)

    async def test_early_exit_is_generic_and_reaped(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaisesRegex(ControlStopped, '^Private control stopped$'):
                await self.runner('early')()

    async def test_trailing_frame_denied(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaises(ControlStopped):
                await self.runner('extra')()

    async def test_output_flood_denied_and_reaped(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaises(ControlStopped):
                await self.runner('flood')()

    async def test_timeout_stops_child(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaises(ControlStopped):
                await self.runner('hold', 2)()
        self.assertTrue(self.children[0].control_ready)

    async def test_reject_stop_escalates(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaises(ControlStopped):
                await self.runner('reject-stop', 2)()
        self.assertTrue(self.children[0].control_ready)
        self.assertNotEqual(self.children[0].returncode, 0)

    async def test_repeated_cancel_joins_before_propagation(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            task = asyncio.create_task(self.runner('reject-stop')())
            while not self.children or not self.children[0].control_ready:
                if task.done():
                    await task
                    self.fail('Child completed before readiness')
                await asyncio.sleep(.001)
            task.cancel()
            await asyncio.sleep(.01)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_cancel_during_spawn_does_not_lose_child(self):
        spawned = asyncio.Event()
        release = asyncio.Event()

        async def slow_spawn(*args, **kwargs):
            child = await self.spawn(*args, **kwargs)
            spawned.set()
            await release.wait()
            return child

        with patch('asyncio.create_subprocess_exec', slow_spawn):
            task = asyncio.create_task(self.runner('hold')())
            await spawned.wait()
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_spawn_failure_is_generic(self):
        async def fail(*args, **kwargs):
            raise OSError('synthetic private diagnostic')
        with patch('asyncio.create_subprocess_exec', fail):
            with self.assertRaisesRegex(ControlStopped, '^Private control stopped$'):
                await self.runner()()

    async def test_no_stdout_or_stderr_from_parent(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with patch('asyncio.create_subprocess_exec', self.spawn):
                with self.assertRaises(ControlStopped):
                    await self.runner('extra')()
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')

    async def test_supervisor_closes_receiver_after_child_failure(self):
        class Receiver:
            closed = False
            async def start(self): pass
            async def wait_private_result(self):
                await asyncio.Future()
            async def close(self): self.closed = True
        receiver = Receiver()
        with patch('asyncio.create_subprocess_exec', self.spawn):
            with self.assertRaises(ValueError):
                await run_local_attempt(receiver, self.runner('early'))
        self.assertTrue(receiver.closed)

    async def test_kill_and_wait_even_if_close_or_terminate_fail(self):
        calls = []
        class Input:
            def write(self, data): calls.append('write')
            async def drain(self): pass
            def close(self):
                calls.append('close')
                raise OSError()
        class Child:
            stdin = Input()
            returncode = None
            waits = 0
            async def wait(self):
                calls.append('wait')
                self.waits += 1
                if self.waits < 3: raise asyncio.TimeoutError()
                self.returncode = -1
                return -1
            def terminate(self):
                calls.append('terminate')
                raise OSError()
            def kill(self): calls.append('kill')
        self.assertTrue(await _reap(Child()))
        self.assertEqual(calls, ['write', 'close', 'wait', 'terminate', 'wait', 'kill', 'wait'])

    async def test_unverifiable_reap_is_failure(self):
        class Child:
            stdin = None
            returncode = None
            async def wait(self): raise OSError()
            def terminate(self): raise OSError()
            def kill(self): raise OSError()
        self.assertTrue(await _reap(Child()))

    async def test_fixture_rejects_malformed_start(self):
        runner = self.runner()
        for frame in [b'WRONG 1\n', b'X' * 64 + b'\n', b'START 1\r\n']:
            child = await self.spawn(self.runtime, str(runner._assembly), 'complete',
                                     stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                     stderr=asyncio.subprocess.DEVNULL, env=_environment())
            try:
                child.stdin.write(frame)
                await child.stdin.drain()
                child.stdin.close()
                self.assertEqual(await asyncio.wait_for(child.stdout.read(1), 2), b'')
                self.assertNotEqual(await asyncio.wait_for(child.wait(), 2), 0)
            finally:
                await _reap(child)

    async def test_fixture_eof_is_not_success(self):
        runner = self.runner()
        child = await self.spawn(self.runtime, str(runner._assembly), 'hold',
                                 stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                                 stderr=asyncio.subprocess.DEVNULL, env=_environment())
        try:
            child.stdin.write(b'START 1\n')
            await child.stdin.drain()
            self.assertEqual(await asyncio.wait_for(child.stdout.readline(), 2), b'READY 1\n')
            child.stdin.close()
            self.assertNotEqual(await asyncio.wait_for(child.wait(), 2), 0)
            self.assertEqual(await child.stdout.read(1), b'')
        finally:
            await _reap(child)

    async def test_reject_invalid_parameters_without_spawn(self):
        for value in [0, -1, True, float('nan'), float('inf'), 31]:
            with self.assertRaises(ControlStopped):
                self.runner(timeout=value)
        with self.assertRaises(ControlStopped):
            SyntheticControlRunner('relative-dotnet')
        with self.assertRaises(ControlStopped):
            self.runner(mode='arbitrary-mode')

    async def test_environment_excludes_secrets_and_loader_hooks(self):
        with patch.dict(os.environ, {'BANK_TOKEN': 'synthetic', 'DOTNET_STARTUP_HOOKS': 'synthetic', 'LD_PRELOAD': 'synthetic'}):
            env = _environment()
        self.assertNotIn('BANK_TOKEN', env)
        self.assertNotIn('DOTNET_STARTUP_HOOKS', env)
        self.assertNotIn('LD_PRELOAD', env)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ControlTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun < 17:
        raise SystemExit(1)
