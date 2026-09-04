/** The tutoring session as React state.
 *
 * `reduce` is a pure function from the current state and one event to the next
 * state, so the whole turn-by-turn behaviour is unit-tested without a network or
 * a component (see useTutoringSession.test.ts). The hook wraps it: it drives the
 * two streaming API calls, dispatches their events into the reducer, and aborts
 * the stream if the component unmounts mid-turn. */

import { useCallback, useEffect, useReducer, useRef } from "react";

import { startSession, submitResponse } from "../../lib/api";
import type {
  MessageKind,
  SeeiStep,
  SessionStatus,
  StreamEvent,
} from "./types";

export type ChatRole = "tutor" | "student" | "fallback";

export interface ChatMessage {
  key: string;
  role: ChatRole;
  step?: SeeiStep;
  kind?: MessageKind;
  content: string;
  /** True while deltas are still arriving; the caret renders on this one. */
  streaming: boolean;
}

/** What the UI can be doing. `awaiting_input` is the only time submit is allowed. */
export type Phase =
  | "idle"
  | "starting"
  | "awaiting_input"
  | "streaming"
  | "terminal"
  | "error";

export interface TutoringState {
  sessionId: string | null;
  status: SessionStatus | null;
  currentStep: SeeiStep | null;
  attemptsUsed: number;
  attemptsLeft: number;
  messages: ChatMessage[];
  phase: Phase;
  error: string | null;
  seq: number; // monotonic, for stable message keys
}

export const initialState: TutoringState = {
  sessionId: null,
  status: null,
  currentStep: null,
  attemptsUsed: 0,
  attemptsLeft: 0,
  messages: [],
  phase: "idle",
  error: null,
  seq: 0,
};

export type Action =
  | { type: "start" }
  | { type: "student"; text: string }
  | { type: "event"; event: StreamEvent };

function pushMessage(
  state: TutoringState,
  msg: Omit<ChatMessage, "key">,
): TutoringState {
  return {
    ...state,
    seq: state.seq + 1,
    messages: [...state.messages, { ...msg, key: String(state.seq) }],
  };
}

/** Append streamed text to the message currently being generated (the last one). */
function appendToLast(state: TutoringState, text: string): TutoringState {
  const messages = state.messages.slice();
  const last = messages[messages.length - 1];
  if (last && last.streaming) {
    messages[messages.length - 1] = { ...last, content: last.content + text };
  }
  return { ...state, messages };
}

function finishLast(state: TutoringState, content: string): TutoringState {
  const messages = state.messages.slice();
  const last = messages[messages.length - 1];
  if (last && last.streaming) {
    messages[messages.length - 1] = { ...last, content, streaming: false };
  }
  return { ...state, messages };
}

export function reduce(state: TutoringState, action: Action): TutoringState {
  switch (action.type) {
    case "start":
      return { ...initialState, phase: "starting" };

    case "student":
      // Echo the student's answer immediately, then wait for the graded reply.
      return pushMessage({ ...state, phase: "streaming" }, {
        role: "student",
        content: action.text,
        streaming: false,
      });

    case "event":
      return applyEvent(state, action.event);
  }
}

function applyEvent(state: TutoringState, event: StreamEvent): TutoringState {
  switch (event.type) {
    case "session":
      return {
        ...state,
        sessionId: event.id,
        status: event.status,
        currentStep: event.current_step,
      };

    case "message_start":
      return pushMessage(state, {
        role: event.kind === "fallback" ? "fallback" : "tutor",
        step: event.step,
        kind: event.kind,
        content: "",
        streaming: true,
      });

    case "delta":
      return appendToLast(state, event.text);

    case "message_end":
      return finishLast(state, event.content);

    case "state":
      return {
        ...state,
        status: event.status,
        currentStep: event.current_step,
        attemptsUsed: event.attempts_used,
        attemptsLeft: event.attempts_left,
        phase: event.terminal ? "terminal" : "awaiting_input",
      };

    case "error":
      return { ...finishLast(state, ""), phase: "error", error: event.detail };
  }
}

export function useTutoringSession(readingId: string) {
  const [state, dispatch] = useReducer(reduce, initialState);
  const abortRef = useRef<AbortController | null>(null);
  // Guard against React 18 StrictMode double-invoking the start effect.
  const startedRef = useRef(false);

  const consume = useCallback(async (stream: AsyncGenerator<StreamEvent>) => {
    for await (const event of stream) {
      dispatch({ type: "event", event });
    }
  }, []);

  const begin = useCallback(async () => {
    dispatch({ type: "start" });
    abortRef.current = new AbortController();
    await consume(startSession(readingId, abortRef.current.signal));
  }, [readingId, consume]);

  const submit = useCallback(
    async (text: string) => {
      if (!state.sessionId) return;
      dispatch({ type: "student", text });
      abortRef.current = new AbortController();
      await consume(
        submitResponse(state.sessionId, text, abortRef.current.signal),
      );
    },
    [state.sessionId, consume],
  );

  useEffect(() => {
    // Fire exactly once. Starting a session creates a database row, so this is
    // not a repeatable effect: it must survive StrictMode's mount/unmount/mount
    // in development, which means it cannot abort on cleanup (that abort would
    // kill the one real start and the guard would stop it restarting). A stream
    // left running on a real unmount simply finishes in the background; its
    // dispatches to an unmounted reducer are no-ops.
    if (startedRef.current) return;
    startedRef.current = true;
    void begin();
  }, [begin]);

  return { state, submit };
}
