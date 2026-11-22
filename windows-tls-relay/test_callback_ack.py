# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Actual .NET duplex children; invented callbacks only, no sockets or provider."""
import asyncio
import contextlib
import io
import os
from pathlib import Path
import struct
import sys
import time
import traceback
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from admin_consent import ConsentAttempt, SetupRejected
from callback_ack import (AckStopped, SyntheticAckRunner, _request_frame,
                          _ack_frame, _read_frame)
from callback_framing import response_bytes
from relay_process import _environment, _reap


class AckTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = os.environ['CONTROL_TEST_DOTNET']
        self.children, self.attempts = [], []
        self.real_spawn = asyncio.create_subprocess_exec
        self.acks = []
        self.data = asyncio.Event()

    def attempt(self, *args, **kwargs):
        a = ConsentAttempt(*args, **kwargs)
        self.attempts.append(a)
        return a

    async def spawn(self, *args, **kwargs):
        self.assertEqual(len(args), 3)
        self.assertTrue(Path(args[0]).is_absolute())
        self.assertEqual(Path(args[1]).name, 'AckFixture.dll')
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['stderr'], asyncio.subprocess.DEVNULL)
        self.assertNotIn('synthetic-private-code', str(args))
        self.assertNotIn('state=', str(args))
        for k in ('DOTNET_STARTUP_HOOKS', 'BANK_TOKEN', 'LD_PRELOAD'):
            self.assertNotIn(k, kwargs['env'])
        c = await self.real_spawn(*args, **kwargs)
        self.children.append(c)
        writer, reader = c.stdin, c.stdout
        outer = self
        class Writer:
            def write(self, value):
                if value.startswith(b'PAA1'):
                    outer.acks.append(value)
                return writer.write(value)
            async def drain(self):
                return await writer.drain()
            def close(self):
                writer.close()
            def is_closing(self):
                return writer.is_closing()
        class Reader:
            async def readexactly(self, n):
                v = await reader.readexactly(n)
                if n != 8:
                    outer.data.set()
                return v
            async def read(self, n):
                return await reader.read(n)
        c.stdin, c.stdout = Writer(), Reader()
        return c

    async def asyncTearDown(self):
        for c in self.children:
            if c.returncode is None:
                await _reap(c)
            self.assertIsNotNone(c.returncode)
            self.assertTrue(c.stdin.is_closing())
        for a in self.attempts:
            self.assertTrue(a.closed)

    def runner(self, mode='complete', timeout=5):
        return SyntheticAckRunner(self.runtime, _mode=mode, timeout=timeout)

    async def run_mode(self, mode='complete', timeout=5):
        with patch('asyncio.create_subprocess_exec', self.spawn), patch('callback_ack.ConsentAttempt', self.attempt):
            return await self.runner(mode, timeout)()

    async def test_real_parser_consent_ack_response(self):
        r = await self.run_mode()
        self.assertIs(r.callback_validated, True)
        self.assertEqual(r.synthetic_browser_response, response_bytes(accepted=True))
        self.assertEqual(self.acks, [b'PAA1\1'])
        self.assertNotIn('synthetic-private-code', repr(r))
        self.assertIn('bank session not confirmed', repr(r))

    async def test_percent_encoding_real_roundtrip(self):
        self.assertTrue((await self.run_mode('encoded')).callback_validated)

    async def test_denial_has_negative_ack_and_fixed_response(self):
        r = await self.run_mode('denied')
        self.assertFalse(r.callback_validated)
        self.assertEqual(self.acks, [b'PAA1\0'])
        self.assertEqual(r.synthetic_browser_response, response_bytes(accepted=False))

    async def test_wrong_state_negative_ack(self):
        self.assertFalse((await self.run_mode('wrong-state')).callback_validated)
        self.assertEqual(self.acks, [b'PAA1\0'])

    async def test_consume_before_ack_and_child_exit_replay_rejected(self):
        consume = ConsentAttempt.consume_callback
        calls = []
        def checked(a, url):
            self.assertEqual(self.acks, [])
            self.assertIsNone(self.children[0].returncode)
            value = consume(a, url)
            with self.assertRaises(SetupRejected):
                consume(a, url)
            calls.append(True)
            return value
        with patch.object(ConsentAttempt, 'consume_callback', checked):
            await self.run_mode()
        self.assertEqual(calls, [True])

    async def before_consume(self, mode):
        with patch.object(ConsentAttempt, 'consume_callback') as consume:
            with self.assertRaises(AckStopped):
                await self.run_mode(mode)
            consume.assert_not_called()
        self.assertEqual(self.acks, [])

    async def test_wrong_host_no_ack(self):
        await self.before_consume('wrong-host')
    async def test_early_exit_no_ack(self):
        await self.before_consume('early')
    async def test_bad_magic_no_ack(self):
        await self.before_consume('bad-magic')
    async def test_oversize_no_ack(self):
        await self.before_consume('oversize')
    async def test_truncated_no_ack(self):
        await self.before_consume('truncated')
    async def test_bad_ascii_no_ack(self):
        await self.before_consume('bad-ascii')

    async def test_nonzero_after_ack_no_receipt_no_revival(self):
        with self.assertRaises(AckStopped):
            await self.run_mode('nonzero')
        self.assertEqual(self.acks, [b'PAA1\1'])
        self.assertTrue(self.attempts[0].closed)

    async def test_trailing_output_after_ack_no_receipt(self):
        with self.assertRaises(AckStopped):
            await self.run_mode('trailing')
        self.assertEqual(self.acks, [b'PAA1\1'])

    async def test_wrong_fixed_response_no_receipt(self):
        with self.assertRaises(AckStopped):
            await self.run_mode('wrong-reply')

    async def test_deadline_before_data_no_consume(self):
        with patch.object(ConsentAttempt, 'consume_callback') as consume:
            with self.assertRaises(AckStopped):
                await self.run_mode('hold-before-data', timeout=1)
            consume.assert_not_called()
        self.assertEqual(self.acks, [])

    async def test_deadline_after_ack_no_receipt(self):
        clock, offset = time.monotonic, [0]
        def ack(value):
            result = _ack_frame(value)
            offset[0] = 20
            return result
        with patch('callback_ack._clock', lambda: clock()+offset[0]), patch('callback_ack._ack_frame', ack):
            with self.assertRaises(AckStopped):
                await self.run_mode('hold-after-ack')
        self.assertEqual(self.acks, [b'PAA1\1'])

    async def test_one_use_no_automatic_retry(self):
        with patch('asyncio.create_subprocess_exec', self.spawn):
            r = self.runner()
            await r()
            with self.assertRaises(AckStopped):
                await r()
        self.assertEqual(len(self.children), 1)

    async def test_repeated_cancel_after_ack_cleanup(self):
        with patch('asyncio.create_subprocess_exec', self.spawn), patch('callback_ack.ConsentAttempt', self.attempt):
            t = asyncio.create_task(self.runner('hold-after-ack')())
            try:
                await asyncio.wait_for(self.data.wait(), 3)
                while not self.acks:
                    if t.done():
                        await t
                    await asyncio.sleep(0)
                t.cancel()
                await asyncio.sleep(0)
                t.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await t
            finally:
                if not t.done():
                    t.cancel()
                await asyncio.gather(t, return_exceptions=True)

    async def test_cancel_during_spawn_retains_child(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed(*args, **kw):
            c = await self.spawn(*args, **kw)
            entered.set()
            await release.wait()
            return c
        with patch('asyncio.create_subprocess_exec', delayed), patch('callback_ack.ConsentAttempt', self.attempt):
            t = asyncio.create_task(self.runner()())
            try:
                await asyncio.wait_for(entered.wait(), 3)
                t.cancel()
                await asyncio.sleep(0)
                t.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await t
            finally:
                release.set()
                if not t.done(): t.cancel()
                await asyncio.gather(t, return_exceptions=True)
        self.assertEqual(self.acks, [])

    async def test_cancel_during_cleanup_no_receipt(self):
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed(c):
            entered.set()
            await release.wait()
            return await _reap(c)
        with patch('callback_ack._reap', delayed), patch('asyncio.create_subprocess_exec', self.spawn):
            t = asyncio.create_task(self.runner()())
            try:
                await asyncio.wait_for(entered.wait(), 3)
                t.cancel()
                await asyncio.sleep(0)
                t.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError): await t
            finally:
                release.set()
                if not t.done(): t.cancel()
                await asyncio.gather(t, return_exceptions=True)

    async def test_cleanup_failure_forbids_receipt(self):
        async def failed(c):
            await _reap(c)
            return True
        with patch('callback_ack._reap', failed):
            with self.assertRaises(AckStopped): await self.run_mode()

    async def test_clock_expiry_after_consume_prevents_ack(self):
        clock = time.monotonic
        offset = [0]
        consume = ConsentAttempt.consume_callback
        def slow(a, url):
            value = consume(a, url)
            offset[0] = 20
            return value
        with patch('callback_ack._clock', lambda: clock()+offset[0]), patch.object(ConsentAttempt, 'consume_callback', slow):
            with self.assertRaises(AckStopped): await self.run_mode()
        self.assertEqual(self.acks, [])

    async def test_expiry_after_cleanup_prevents_receipt(self):
        clock, offset = time.monotonic, [0]
        async def slow(c):
            value = await _reap(c)
            offset[0] = 20
            return value
        with patch('callback_ack._clock', lambda: clock()+offset[0]), patch('callback_ack._reap', slow):
            with self.assertRaises(AckStopped): await self.run_mode()
        self.assertEqual(self.acks, [b'PAA1\1'])

    async def test_public_failure_output_value_free(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                await self.run_mode('nonzero')
            except AckStopped as e:
                text = ''.join(traceback.format_exception(e))
                self.assertNotIn('synthetic-private-code', text)
                self.assertNotIn('state=', text)
                self.assertIsNone(e.__cause__)
            else: self.fail('accepted nonzero child')
        self.assertEqual(out.getvalue()+err.getvalue(), '')
        self.assertEqual(repr(self.runner()), '<SyntheticAckRunner private>')

    async def test_configuration_and_wire_type_bounds(self):
        for v in (0, -1, True, float('nan'), float('inf'), 31):
            with self.assertRaises(AckStopped): self.runner(timeout=v)
        for v in (None, b'', 'raw', bytearray(b'x'), b'x'*12289):
            with self.assertRaises(AckStopped): _request_frame(v)
        for v in (None, 0, 1, 'true'):
            with self.assertRaises(AckStopped): _ack_frame(v)
        self.assertEqual(_ack_frame(True), b'PAA1\1')
        self.assertEqual(_request_frame(b'x'), b'PAI1\0\0\0\1x')
        with self.assertRaises(AckStopped): SyntheticAckRunner('dotnet')
        with self.assertRaises(AckStopped): self.runner('arbitrary-command')
        self.assertEqual(self.children, [])

    async def raw_child(self, raw, ack):
        r = self.runner()
        c = await self.spawn(self.runtime, str(r._assembly), 'complete',
                             stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                             stderr=asyncio.subprocess.DEVNULL, env=_environment())
        try:
            c.stdin.write(raw)
            await c.stdin.drain()
            if ack is not None:
                async def bounded(a): return await asyncio.wait_for(a, 3)
                await _read_frame(c.stdout, b'PAD1', 8192, bounded)
                c.stdin.write(ack)
                await c.stdin.drain()
            c.stdin.close()
            rest = await asyncio.wait_for(c.stdout.read(4096), 3)
            code = await asyncio.wait_for(c.wait(), 3)
            return rest, code
        finally: await _reap(c)

    async def test_actual_child_rejects_missing_truncated_duplicate_ack(self):
        raw = _request_frame(b'GET /callback?state=x&code=y HTTP/1.1\r\nHost: localhost:8765\r\n\r\n')
        for ack in (b'', b'PAA1', b'BAD!\1', b'PAA1\2', b'PAA1\1X', b'PAA1\1PAA1\1'):
            rest, code = await self.raw_child(raw, ack)
            self.assertEqual(rest, b'')
            self.assertNotEqual(code, 0)

    async def test_actual_child_both_ack_values_match_python_response(self):
        raw = _request_frame(b'GET /callback?state=x&code=y HTTP/1.1\r\nHost: localhost:8765\r\n\r\n')
        for accepted in (False, True):
            rest, code = await self.raw_child(raw, _ack_frame(accepted))
            expected = response_bytes(accepted=accepted)
            self.assertEqual(rest, b'PAR1'+struct.pack('!I', len(expected))+expected)
            self.assertEqual(code, 0)

    async def test_actual_child_rejects_bad_request_frames(self):
        for raw in (b'', b'PAI1', b'BAD!\0\0\0\1x', b'PAI1\0\0\0\0', b'PAI1\xff\xff\xff\xff', b'PAI1\0\0\0\x10x'):
            rest, code = await self.raw_child(raw, None)
            self.assertEqual(rest, b'')
            self.assertNotEqual(code, 0)

    async def test_child_waits_for_ack_before_any_response(self):
        r = self.runner()
        raw = _request_frame(b'GET /callback?state=x&code=y HTTP/1.1\r\nHost: localhost:8765\r\n\r\n')
        c = await self.spawn(self.runtime, str(r._assembly), 'complete',
                             stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                             stderr=asyncio.subprocess.DEVNULL, env=_environment())
        pending = None
        try:
            async def bounded(a): return await asyncio.wait_for(a, 3)
            c.stdin.write(raw); await c.stdin.drain()
            await _read_frame(c.stdout, b'PAD1', 8192, bounded)
            pending = asyncio.create_task(c.stdout.readexactly(8))
            # Bounded observation supplements the child protocol code, not a timing proof.
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), .05)
            self.assertIsNone(c.returncode)
            c.stdin.write(_ack_frame(False)); await c.stdin.drain(); c.stdin.close()
            header = await asyncio.wait_for(pending, 3)
            self.assertEqual(header[:4], b'PAR1')
            n = struct.unpack('!I', header[4:])[0]
            self.assertEqual(await c.stdout.readexactly(n), response_bytes(accepted=False))
            self.assertEqual(await c.stdout.read(1), b'')
            self.assertEqual(await asyncio.wait_for(c.wait(), 3), 0)
        finally:
            if pending is not None and not pending.done(): pending.cancel()
            if pending is not None: await asyncio.gather(pending, return_exceptions=True)
            await _reap(c)

    async def test_spawn_failure_generic_no_ack(self):
        async def fail(*args, **kwargs):
            raise OSError('synthetic private diagnostic')
        with patch('asyncio.create_subprocess_exec', fail), patch('callback_ack.ConsentAttempt', self.attempt):
            with self.assertRaisesRegex(AckStopped, '^Private callback acknowledgement stopped$'):
                await self.runner()()
        self.assertEqual(self.acks, [])

    async def test_frame_reader_bounds_direction_and_truncation(self):
        async def bounded(a): return await a
        for raw in (b'', b'PAD1', b'PAR1\0\0\0\1x', b'PAD1\0\0\0\0', b'PAD1\xff\xff\xff\xff', b'PAD1\0\0\0\2x'):
            reader = asyncio.StreamReader()
            reader.feed_data(raw); reader.feed_eof()
            with self.assertRaises((AckStopped, asyncio.IncompleteReadError)):
                await _read_frame(reader, b'PAD1', 8192, bounded)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AckTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful() or result.skipped or result.testsRun < 31:
        raise SystemExit(1)
