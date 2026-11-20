"""Internal cancellation boundary. No I/O, imports of provider clients or retries."""
import asyncio


def _retrieve_owned_result(task):
    # Also retrieve a result after repeated caller cancellation interrupts drain.
    if not task.cancelled():
        task.exception()


async def _await_owned(coro, seconds):
    """Keep caller cancellation/timeout separate from transport cleanup failures.

    Drain cancellation cooperatively, as wait_for already does. This is not a
    hard wall-clock bound for a transport that refuses to finish cleanup.
    """
    task = asyncio.ensure_future(coro)
    task.add_done_callback(_retrieve_owned_result)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=seconds)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        task.cancel()
        try:
            await task
        except (Exception, asyncio.CancelledError):
            pass
        raise

