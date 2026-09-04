/** The typed client for the session API.
 *
 * Two actions stream (start a session, submit a response) and are async
 * generators of typed events; two reads return JSON. Requests are same-origin:
 * in development Vite proxies them to the backend, in production it is one
 * service, so no base URL is needed. */

import { readSSE } from "./sse";
import type {
  ReadingDetail,
  ReadingListItem,
} from "../features/readings/types";
import type {
  SessionState,
  StreamEvent,
  TutorMessageRow,
} from "../features/tutoring/types";

/** Map a raw SSE event to a typed StreamEvent, tagging the payload with `type`. */
function toStreamEvent(event: string, data: string): StreamEvent {
  const payload = data ? JSON.parse(data) : {};
  return { type: event, ...payload } as StreamEvent;
}

async function* streamPost(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    // The connection never opened (backend down, network error). An abort is a
    // deliberate teardown, not a failure, so it stays silent.
    if (signal?.aborted) return;
    yield { type: "error", detail: `could not reach the server: ${errorName(e)}` };
    return;
  }

  if (!response.ok) {
    // A non-2xx never opens a stream; surface it as an error event so callers
    // handle one failure shape, not two.
    yield { type: "error", detail: `request failed: ${response.status}` };
    return;
  }

  try {
    for await (const raw of readSSE(response)) {
      yield toStreamEvent(raw.event, raw.data);
    }
  } catch (e) {
    // The stream broke mid-flight. Again, an abort is intentional.
    if (signal?.aborted) return;
    yield { type: "error", detail: `stream interrupted: ${errorName(e)}` };
  }
}

function errorName(e: unknown): string {
  return e instanceof Error ? e.name : "unknown error";
}

/** Start a session for a reading. Streams the opening Prompt. */
export function startSession(
  readingId: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  return streamPost("/sessions", { reading_id: readingId }, signal);
}

/** Submit one response. Streams the Tutor's reply and the new session state. */
export function submitResponse(
  sessionId: string,
  text: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  return streamPost(`/sessions/${sessionId}/responses`, { text }, signal);
}

export async function getReadings(): Promise<ReadingListItem[]> {
  const response = await fetch("/readings");
  if (!response.ok) throw new Error(`readings: ${response.status}`);
  return response.json();
}

export async function getReading(readingId: string): Promise<ReadingDetail> {
  const response = await fetch(`/readings/${readingId}`);
  if (!response.ok) throw new Error(`reading ${readingId}: ${response.status}`);
  return response.json();
}

export async function getSession(sessionId: string): Promise<SessionState> {
  const response = await fetch(`/sessions/${sessionId}`);
  if (!response.ok) throw new Error(`session ${sessionId}: ${response.status}`);
  return response.json();
}

export async function getMessages(sessionId: string): Promise<TutorMessageRow[]> {
  const response = await fetch(`/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error(`messages ${sessionId}: ${response.status}`);
  return response.json();
}
