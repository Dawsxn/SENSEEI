"""The trial chatbot group's conversation, streamed.

A plain chat on the agents' model (docs/context/trial.md). The model is sent the
whole conversation each turn, with the participant's reading as its system
prompt: the reading and nothing else, no teaching instructions.

Like the tutoring loop, the reply streams as Server-Sent Events from a database
session the stream opens itself:

    message_start  the reply begins
    delta          a piece of its text
    message_end    the reply is complete: its stored id and full content
    error          something failed; the stream ends

The participant's message is stored before the model is called, so the record
holds what they sent even if no reply came. A reply that fails partway is not
stored; a `turn_failed` event records that it happened.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from starlette.concurrency import iterate_in_threadpool

from agents.providers.base import LLMProvider

from ..db import sessionmaker
from ..models import ChatMessage, Reading
from . import trial_service
from .provider_errors import log_failure


#: The chatbot's whole system prompt. It hands over the reading and says no more:
#: how to help is left to the model, as a general-purpose chatbot would.
SYSTEM_PROMPT = (
    "The user is studying the reading below. Use it as context when it is "
    "relevant to what they ask.\n\n"
    "--- READING: {title} ---\n{content}\n--- END OF READING ---"
)


async def _system_prompt(db, class_id: uuid.UUID) -> str | None:
    reading_id = await trial_service._their_reading(db, class_id)
    reading = await db.get(Reading, reading_id) if reading_id else None
    if reading is None:
        return None
    return SYSTEM_PROMPT.format(title=reading.title, content=reading.content)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def send(user_id: uuid.UUID, text: str, model: LLMProvider) -> AsyncIterator[str]:
    """Store the participant's message, then stream and store the reply."""
    async with sessionmaker()() as db:
        refused = await trial_service.refuse_chat(db, user_id)
        if refused is not None:
            yield _sse("error", {"detail": refused})
            return
        participant = await trial_service.participant_for(db, user_id)
        assert participant is not None  # refuse_chat checked

        db.add(ChatMessage(participant_id=participant.id, role="user", content=text))
        await db.commit()
        history = await trial_service.chat_history(db, user_id)
        turns = [(m.role, m.content) for m in history]
        system = await _system_prompt(db, participant.class_id)

        yield _sse("message_start", {})
        pieces: list[str] = []
        try:
            async for chunk in iterate_in_threadpool(model.chat_stream(turns, system)):
                pieces.append(chunk)
                yield _sse("delta", {"text": chunk})
        except Exception as e:  # a provider failure mid-reply
            log_failure("chatbot", e)
            await trial_service.note(db, user_id, "turn_failed", {"where": "chatbot"})
            yield _sse("error", {"detail": f"chatbot failed: {type(e).__name__}"})
            return

        content = "".join(pieces).strip()
        reply = ChatMessage(participant_id=participant.id, role="assistant", content=content)
        db.add(reply)
        await db.commit()
        yield _sse("message_end", {"id": str(reply.id), "content": content})
