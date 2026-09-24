/** The typed client for the session API.
 *
 * Two actions stream (start a session, submit a response) and are async
 * generators of typed events; two reads return JSON. Requests are same-origin:
 * in development Vite proxies them to the backend, in production it is one
 * service, so no base URL is needed. */

import { readSSE } from "./sse";
import type {
  AuthConfig,
  AuthUser,
  DevUser,
} from "../features/auth/types";
import type {
  ReadingDetail,
  ReadingListItem,
  ReadingSessionItem,
} from "../features/readings/types";
import type {
  ClassDetail,
  ClassFields,
  ClassListItem,
  JoinResult,
} from "../features/classes/types";
import type {
  ExtractResult,
  LibraryItem,
  LibraryReading,
  NewReading,
} from "../features/library/types";
import type { SessionTranscript } from "../features/review/types";
import type { Rubric } from "../features/tutoring/types";
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

// --- auth --------------------------------------------------------------------

export async function getMe(): Promise<AuthUser> {
  const response = await fetch("/auth/me");
  if (!response.ok) throw new Error(`me: ${response.status}`);
  return response.json();
}

export async function getAuthConfig(): Promise<AuthConfig> {
  const response = await fetch("/auth/config");
  if (!response.ok) throw new Error(`auth config: ${response.status}`);
  return response.json();
}

export async function getDevUsers(): Promise<DevUser[]> {
  const response = await fetch("/auth/dev/users");
  if (!response.ok) throw new Error(`dev users: ${response.status}`);
  return response.json();
}

export async function devLogin(userId: string): Promise<void> {
  const response = await fetch("/auth/dev/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  if (!response.ok) throw new Error(`dev login: ${response.status}`);
}

export async function logout(): Promise<void> {
  await fetch("/auth/logout", { method: "POST" });
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

/** Where a reading's original PDF is served from.
 *
 * A URL rather than a fetch: the viewer and the download link both hand it
 * straight to the browser, which streams and caches it far better than we would
 * by pulling the bytes through JavaScript. */
export function readingFileUrl(readingId: string): string {
  return `/readings/${readingId}/file`;
}

/** The rubric this deployment grades against. Not session-scoped: the version
 *  is a setting, not something a request chooses. */
export async function getRubric(): Promise<Rubric> {
  const response = await fetch("/rubric");
  if (!response.ok) throw new Error(`rubric: ${response.status}`);
  return response.json();
}

export async function getReadingSessions(
  readingId: string,
): Promise<ReadingSessionItem[]> {
  const response = await fetch(`/readings/${readingId}/sessions`);
  if (!response.ok) throw new Error(`sessions ${readingId}: ${response.status}`);
  return response.json();
}

export async function getTranscript(sessionId: string): Promise<SessionTranscript> {
  const response = await fetch(`/sessions/${sessionId}/transcript`);
  if (!response.ok) throw new Error(`transcript ${sessionId}: ${response.status}`);
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

// --- classes and enrolment ------------------------------------------------------

/** A failed request that callers need to tell apart by status: a 409 duplicate
 *  class and a 404 join code each get their own message, not a generic one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    /** The backend's `detail` when it is a code worth branching on. */
    readonly detail: string = "",
  ) {
    super(message);
  }
}

async function send<T>(path: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return settle<T>(response, `${method} ${path}`);
}

/** A multipart POST, for uploads. The browser sets the boundary header itself. */
async function sendForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(path, { method: "POST", body: form });
  return settle<T>(response, `POST ${path}`);
}

/** The body of a successful response, or an ApiError carrying the status and
 *  the backend's `detail`, which for uploads is a code like `no_text`. */
async function settle<T>(response: Response, what: string): Promise<T> {
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // not JSON; the status is enough
    }
    throw new ApiError(response.status, `${what}: ${response.status}`, detail);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

export const getClasses = () => send<ClassListItem[]>("/instructor/classes", "GET");
export const getClass = (id: string) => send<ClassDetail>(`/instructor/classes/${id}`, "GET");
export const createClass = (fields: ClassFields) =>
  send<ClassListItem>("/instructor/classes", "POST", fields);
export const updateClass = (id: string, fields: ClassFields) =>
  send<ClassDetail>(`/instructor/classes/${id}`, "PATCH", fields);
export const deleteClass = (id: string) => send<void>(`/instructor/classes/${id}`, "DELETE");
export const replaceJoinCode = (id: string) =>
  send<{ join_code: string }>(`/instructor/classes/${id}/join-code`, "POST");
export const removeStudent = (classId: string, studentId: string) =>
  send<void>(`/instructor/classes/${classId}/students/${studentId}`, "DELETE");
export const joinClass = (joinCode: string) =>
  send<JoinResult>("/enrolments", "POST", { join_code: joinCode });

// --- an instructor's readings -------------------------------------------------

export const getLibrary = () => send<LibraryItem[]>("/instructor/readings", "GET");
export const getLibraryReading = (id: string) =>
  send<LibraryReading>(`/instructor/readings/${id}`, "GET");
export const libraryFileUrl = (id: string) => `/instructor/readings/${id}/file`;

/** The PDF as text, with its figures described. Saves nothing. */
export function extractReading(file: File): Promise<ExtractResult> {
  const form = new FormData();
  form.append("file", file);
  return sendForm<ExtractResult>("/instructor/readings/extract", form);
}

export function createReading(reading: NewReading): Promise<{ id: string }> {
  const form = new FormData();
  form.append("file", reading.file);
  form.append("title", reading.title);
  if (reading.description) form.append("description", reading.description);
  form.append("content", reading.content);
  reading.coreComponents.forEach((c) => form.append("core_components", c));
  reading.classIds.forEach((id) => form.append("class_ids", id));
  return sendForm<{ id: string }>("/instructor/readings", form);
}

export const updateLibraryReading = (
  id: string,
  fields: { title: string; description: string | null },
) => send<LibraryReading>(`/instructor/readings/${id}`, "PATCH", fields);
export const setReadingClasses = (id: string, classIds: string[]) =>
  send<LibraryReading>(`/instructor/readings/${id}/classes`, "PUT", { class_ids: classIds });
export const deleteLibraryReading = (id: string) =>
  send<void>(`/instructor/readings/${id}`, "DELETE");
