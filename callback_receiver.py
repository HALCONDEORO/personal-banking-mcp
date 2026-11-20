# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Explicit loopback-only callback receiver. No TLS/SSH/provider or autostart.

Private local-hop prototype, not an MCP tool. The selected design keeps the
future TLS relay and admin workflow on the same Windows laptop, without SSH.
It expects a fixed request rebuilt by a separately reviewed TLS relay. Loopback
and a fixed Host are not authentication against competing local processes.
"""
import asyncio
from callback_framing import parse_relay_request,response_bytes,CallbackRejected,MAX_REQUEST
from admin_consent import SetupRejected

class ReceiverStopped(ValueError):pass

def stopped():raise ReceiverStopped('Callback receiver stopped') from None

class CallbackReceiver:
    __slots__=('_attempt','_server','_future','_connections','_busy','_tasks','_read_seconds','_lifetime','_port','_expiry')
    def __init__(self,attempt,*,port=8766,read_seconds=2.0,lifetime_seconds=300):
        if (type(port) is not int or not 0<=port<=65535
                or type(read_seconds) not in {int,float} or not 0<read_seconds<=2
                or type(lifetime_seconds) not in {int,float} or not 0<lifetime_seconds<=300):stopped()
        self._attempt=attempt;self._port=port;self._read_seconds=read_seconds;self._lifetime=lifetime_seconds
        self._server=None;self._future=None;self._connections=0;self._busy=False;self._tasks=set();self._expiry=None
    def __repr__(self):return '<CallbackReceiver private>'
    @property
    def port(self):
        if self._server is None:stopped()
        return self._server.sockets[0].getsockname()[1]
    async def start(self):
        if self._future is not None or self._attempt.closed:stopped()
        self._future=asyncio.get_running_loop().create_future()
        try:
            self._server=await asyncio.start_server(self._handle,'127.0.0.1',self._port,limit=MAX_REQUEST+1)
            self._expiry=asyncio.create_task(self._expire())
        except Exception:
            await self.close();stopped()
    async def _expire(self):
        await asyncio.sleep(min(self._lifetime,self._attempt.remaining_seconds))
        await self.close()
    async def wait_private_result(self):
        if self._future is None:stopped()
        try:return await asyncio.shield(self._future)
        except asyncio.CancelledError:stopped()
        finally:await self.close()
    def _stop_accepting(self):
        if self._server is not None:self._server.close()
    async def _handle(self,reader,writer):
        task=asyncio.current_task();self._tasks.add(task)
        accepted=False;private=None;owns_slot=False
        try:
            self._connections+=1
            if self._busy or self._connections>8 or self._future.done():return
            self._busy=True;owns_slot=True
            # Half-close required: consume through EOF, never ignore a body.
            async def bounded_read():
                parts=[];size=0
                while True:
                    chunk=await reader.read(min(4096,MAX_REQUEST+1-size))
                    if not chunk:return b''.join(parts)
                    size+=len(chunk)
                    if size>MAX_REQUEST:raise CallbackRejected('Callback request rejected')
                    parts.append(chunk)
            raw=await asyncio.wait_for(bounded_read(),self._read_seconds)
            private=self._attempt.consume_callback(parse_relay_request(raw))
            accepted=True
        except (CallbackRejected,SetupRejected,asyncio.TimeoutError,OSError):pass
        finally:
            # Stop accept immediately, even if the peer never reads our reply.
            terminal=accepted or self._attempt.closed or self._connections>=8
            if terminal:self._stop_accepting()
            try:
                writer.write(response_bytes(accepted=accepted))
                await asyncio.wait_for(writer.drain(),0.25)
            except (OSError,asyncio.TimeoutError):pass
            writer.close()
            try:await asyncio.wait_for(writer.wait_closed(),0.25)
            except (OSError,asyncio.TimeoutError):pass
            if owns_slot:self._busy=False
            if accepted and not self._future.done():self._future.set_result(private)
            elif terminal and not self._future.done():self._future.cancel()
            self._tasks.discard(task)
    async def close(self):
        if self._server is not None:
            self._server.close();await self._server.wait_closed();self._server=None
        current=asyncio.current_task()
        tasks=[t for t in self._tasks if t is not current]
        if self._expiry is not None and self._expiry is not current:tasks.append(self._expiry)
        for task in tasks:task.cancel()
        if tasks:await asyncio.gather(*tasks,return_exceptions=True)
        if self._future is not None and not self._future.done():self._future.cancel()
        self._attempt.cancel()
