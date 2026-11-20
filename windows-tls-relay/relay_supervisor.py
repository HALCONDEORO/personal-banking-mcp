# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Marco Antonio Tevar Asensio
"""Cooperative lifecycle join. No launcher, live setup or detached-child claim."""
import asyncio


class LocalAttemptStopped(ValueError):
    pass


async def _cleanup(receiver, tasks):
    """Independent cleanup stages, even if receiver closure fails."""
    close_failed = False
    try:
        await receiver.close()
    except (Exception, asyncio.CancelledError):
        close_failed = True
    finally:
        # Cancel/join ALWAYS runs, including after uncertain receiver closure.
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    return close_failed


async def run_local_attempt(receiver, run_relay):
    """Close receiver on every exit; always cancel/join owned cooperative tasks.

    run_relay is a zero-argument async callable invoked after the receiver binds.
    It MUST honor cancellation and must not detach work. Windows process launch
    and child containment are not supplied. Failure to close a receiver remains
    an error, never a claim that its listener was closed.
    """
    tasks = []
    cancelled = False
    failed = False
    result = None
    try:
        await receiver.start()
        private = asyncio.create_task(receiver.wait_private_result())
        tasks.append(private)
        relay = asyncio.create_task(run_relay())
        tasks.append(relay)
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        if relay in done:
            await relay
            result = await asyncio.wait_for(asyncio.shield(private), 0.25)
        else:
            result = await private
            await asyncio.wait_for(asyncio.shield(relay), 0.25)
    except asyncio.CancelledError:
        cancelled = True
    except Exception:
        failed = True
    finally:
        # Shield a separately owned cleanup task so repeated cancellation of
        # this caller cannot skip task cancellation/join or interrupt close.
        cleanup = asyncio.create_task(_cleanup(receiver, tasks))
        while True:
            try:
                close_failed = await asyncio.shield(cleanup)
                break
            except asyncio.CancelledError:
                cancelled = True
        if cancelled:
            raise asyncio.CancelledError() from None
        if failed or close_failed:
            raise LocalAttemptStopped('Local attempt stopped') from None
    return result
