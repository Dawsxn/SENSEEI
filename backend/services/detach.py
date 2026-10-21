"""Keep a streamed turn running when the browser stops listening.

A streaming response's generator is cancelled the moment its client goes away:
a closed laptop lid, a dropped Wi-Fi, a reload mid-reply. Without this, that
cancellation lands wherever the turn happened to be, and can leave a session
without its opening question, or a graded answer without its reply.

`detached` runs the turn as its own task and streams from it. If the client
leaves, only the streaming stops; the turn finishes and saves everything, and
the student finds it all there when they come back.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

#: Running turns, held so the event loop does not garbage-collect a task whose
#: listener has gone.
_running: set[asyncio.Task] = set()

_DONE = object()


async def detached(events: AsyncIterator[str]) -> AsyncIterator[str]:
    """Yield `events`, produced by a task that outlives this generator."""
    queue: asyncio.Queue = asyncio.Queue()

    async def run() -> None:
        try:
            async for event in events:
                await queue.put(event)
        finally:
            await queue.put(_DONE)

    task = asyncio.create_task(run())
    _running.add(task)
    task.add_done_callback(_running.discard)

    while True:
        event = await queue.get()
        if event is _DONE:
            break
        yield event
    # Surface a crash in the turn itself, as the undetached stream would have.
    if task.done() and not task.cancelled() and task.exception() is not None:
        raise task.exception()
