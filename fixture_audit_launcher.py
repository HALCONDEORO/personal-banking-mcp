"""Test-only stdio launcher with networking denied after event-loop creation.

Windows event-loop infrastructure can need local sockets during construction.
Create that infrastructure first; no fixture/provider code is imported before
installing the audit hook. This is not an OS sandbox or a live-bank launcher.
"""
import asyncio
import runpy
import sys


def main():
    loop = asyncio.new_event_loop()
    base = type(asyncio.get_event_loop_policy())

    class PreparedLoopPolicy(base):
        def new_event_loop(self):
            if self.used:
                raise RuntimeError('Unexpected additional test event loop')
            self.used = True
            return loop

    policy = PreparedLoopPolicy()
    policy.used = False
    asyncio.set_event_loop_policy(policy)

    def deny_network(event, args):
        if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo'}:
            raise PermissionError('Network forbidden in fixture test')

    sys.addaudithook(deny_network)
    try:
        runpy.run_path(sys.argv[1], run_name='__main__')
    finally:
        if not loop.is_closed():
            loop.close()


if __name__ == '__main__':
    main()
