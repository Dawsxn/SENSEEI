/** The tutoring session as React state.
 *
 * `reduce` is a pure function from the current state and one event to the next
 * state, so the whole turn-by-turn behaviour is unit-tested without a network or
 * a component (see useTutoringSession.test.ts). The hook wraps it: it drives the
 * two streaming API calls, dispatches their events into the reducer, and aborts
 * the stream if the component unmounts mid-turn.
 *
 * A reload is not leaving. A trial participant has one session, so the hook
 * picks theirs back up from the server. Anyone else's tab remembers which
 * session it is in (`remember`), for as long as the tab is open, so a reload
 * picks that one up too; closing the tab forgets it, and pressing Done on the
 * reading step starts a new one. */

import { useCallback, useEffect, useReducer, useRef } from "react";

import { ApiError, getSession, getTranscript, startSession, submitResponse } from "../../lib/api";
import { logTrial } from "../trial/trialLog";
import type { SessionTranscript } from "../review/types";
import type {
  MessageKind,
  SeeiStep,
  SessionStatus,
  StreamEvent,
} from "./types";
import { MAX_ATTEMPTS } from "./types";

export type ChatRole = "tutor" | "student" | "fallback";

export interface ChatMessage {
  key: string;
  role: ChatRole;
  step?: SeeiStep;
  kind?: MessageKind;
  content: string;
  /** Criteria this attempt missed, shown beside the message. Empty on anything
   *  that is not feedback on a failure. */
  unmet: string[];
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
  | { type: "event"; event: StreamEvent }
  /** Try again: waiting on the server again, without clearing the chat. */
  | { type: "retry" }
  | {
      type: "resume";
      transcript: SessionTranscript;
      status: SessionStatus;
      currentStep: SeeiStep;
      withTags?: boolean;
    };

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
        unmet: [],
        streaming: false,
      });

    case "event":
      return applyEvent(state, action.event);

    case "retry":
      return { ...state, phase: "streaming", error: null };

    case "resume":
      return resume(action.transcript, action.status, action.currentStep, action.withTags);
  }
}

/** A session picked back up after a reload, from its stored transcript.
 *
 * With `withTags`, the criteria an answer missed come back as the tags on the
 * reply that followed it, as they showed live. Without (the trial, as it ran),
 * only the replies come back. */
export function resume(
  transcript: SessionTranscript,
  status: SessionStatus,
  currentStep: SeeiStep,
  withTags = false,
): TutoringState {
  let missed: string[] = [];
  const messages: ChatMessage[] = transcript.timeline.map((entry, i) => {
    let unmet: string[] = [];
    if (entry.role === "student") {
      missed = (entry.judgment?.criteria ?? []).filter((c) => !c.passed).map((c) => c.criterion);
    } else {
      if (withTags && entry.role === "tutor") unmet = missed;
      missed = [];
    }
    return {
      key: `r${i}`,
      role: entry.role,
      step: entry.step,
      content: entry.content,
      unmet,
      streaming: false,
    };
  });
  const used = transcript.timeline.filter(
    (e) => e.role === "student" && e.step === currentStep,
  ).length;
  return {
    ...initialState,
    sessionId: transcript.id,
    status,
    currentStep,
    attemptsUsed: used,
    attemptsLeft: Math.max(MAX_ATTEMPTS - used, 0),
    messages,
    phase: status === "in_progress" ? "awaiting_input" : "terminal",
    seq: messages.length,
  };
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
        unmet: event.unmet ?? [],
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

interface Options {
  /** Pick up this session rather than starting one. */
  resumeId?: string | null;
  /** Hold off until the caller knows whether there is one to resume. */
  wait?: boolean;
  /** Outside the trial: remember this tab's session, so a reload picks it back
   *  up, and bring back the criteria tags with it. */
  remember?: boolean;
}

/** Where the tab keeps the session it is in, one per reading. Session storage,
 *  so it lasts through a reload and goes when the tab closes. */
const storageKey = (readingId: string) => `senseei.session.${readingId}`;

function recall(readingId: string): string | null {
  try {
    return sessionStorage.getItem(storageKey(readingId));
  } catch {
    return null;
  }
}

function keep(readingId: string, sessionId: string) {
  try {
    sessionStorage.setItem(storageKey(readingId), sessionId);
  } catch {
    // Without storage a reload starts over, which is how it used to be.
  }
}

/** Forget the tab's session on a reading, so the next visit starts a new one:
 *  on Done from the reading step, and on leaving. */
export function forgetSession(readingId: string) {
  try {
    sessionStorage.removeItem(storageKey(readingId));
  } catch {
    // nothing kept, nothing to forget
  }
}

const isMissing = (e: unknown) => e instanceof ApiError && e.status === 404;

export function useTutoringSession(readingId: string, options: Options = {}) {
  const { resumeId = null, wait = false, remember = false } = options;
  const [state, dispatch] = useReducer(reduce, initialState);
  const abortRef = useRef<AbortController | null>(null);
  // Guard against React 18 StrictMode double-invoking the start effect.
  const startedRef = useRef(false);
  // The answer in flight, and how many answers the chat held before it, so Try
  // again can tell whether the server got it. Cleared when its reply lands.
  const pendingRef = useRef<{ text: string; before: number } | null>(null);
  const stateRef = useRef(state);
  stateRef.current = state;

  const consume = useCallback(
    async (stream: AsyncGenerator<StreamEvent>) => {
      for await (const event of stream) {
        dispatch({ type: "event", event });
        if (event.type === "session" && remember) keep(readingId, event.id);
        if (event.type === "state") pendingRef.current = null;
        // A turn's last event: the reply has finished arriving, and the student
        // can read it. Logged here, not from the screen's state, so picking a
        // session back up after a reload is not mistaken for a new reply. (A
        // no-op unless this is a trial participant.)
        if (event.type === "state") logTrial("reply_shown");
      }
    },
    [readingId, remember],
  );

  /** Load a session from the server into the chat, as it stands there. */
  const load = useCallback(
    async (id: string) => {
      const [transcript, session] = await Promise.all([getTranscript(id), getSession(id)]);
      dispatch({
        type: "resume",
        transcript,
        status: session.status,
        currentStep: session.current_step,
        withTags: remember,
      });
      return transcript;
    },
    [remember],
  );

  const fresh = useCallback(async () => {
    dispatch({ type: "start" });
    abortRef.current = new AbortController();
    await consume(startSession(readingId, abortRef.current.signal));
  }, [readingId, consume]);

  const begin = useCallback(async () => {
    dispatch({ type: "start" });
    if (resumeId) {
      try {
        await load(resumeId);
      } catch {
        dispatch({
          type: "event",
          event: { type: "error", detail: "could not load your session" },
        });
      }
      return;
    }
    const kept = remember ? recall(readingId) : null;
    if (kept) {
      try {
        const session = await getSession(kept);
        // Left or abandoned is over for good: start a new one instead.
        if (session.status !== "left" && session.status !== "abandoned") {
          await load(kept);
          return;
        }
      } catch (e) {
        if (!isMissing(e)) {
          dispatch({
            type: "event",
            event: { type: "error", detail: "could not load your session" },
          });
          return;
        }
      }
      forgetSession(readingId);
    }
    await fresh();
  }, [readingId, resumeId, remember, consume, load, fresh]);

  const submit = useCallback(
    async (text: string, timeUp = false) => {
      if (!state.sessionId) return;
      pendingRef.current = {
        text,
        before: state.messages.filter((m) => m.role === "student").length,
      };
      dispatch({ type: "student", text });
      abortRef.current = new AbortController();
      await consume(
        submitResponse(state.sessionId, text, abortRef.current.signal, timeUp),
      );
    },
    [state.sessionId, state.messages, consume],
  );

  /** Try again, after an error. Not a reload, which would show the same thing
   *  less smoothly: the session is loaded back from the server as it stands,
   *  and an answer the server never got is sent again, so nothing is typed
   *  twice and nothing is counted twice. With no session yet, it starts one. */
  const retry = useCallback(async () => {
    const id = stateRef.current.sessionId;
    if (!id) return begin();
    const pending = pendingRef.current;
    dispatch({ type: "retry" });
    try {
      const transcript = await load(id);
      const answers = transcript.timeline.filter((e) => e.role === "student").length;
      if (pending && answers === pending.before && transcript.status === "in_progress") {
        dispatch({ type: "student", text: pending.text });
        abortRef.current = new AbortController();
        await consume(submitResponse(id, pending.text, abortRef.current.signal));
      } else {
        pendingRef.current = null;
      }
    } catch (e) {
      if (isMissing(e)) {
        // Its opening never arrived, so the server removed it: start again.
        forgetSession(readingId);
        return fresh();
      }
      dispatch({
        type: "event",
        event: { type: "error", detail: "could not reach the server" },
      });
    }
  }, [readingId, begin, load, consume, fresh]);

  useEffect(() => {
    // Fire exactly once. Starting a session creates a database row, so this is
    // not a repeatable effect: it must survive StrictMode's mount/unmount/mount
    // in development, which means it cannot abort on cleanup (that abort would
    // kill the one real start and the guard would stop it restarting). A stream
    // left running on a real unmount simply finishes in the background; its
    // dispatches to an unmounted reducer are no-ops.
    if (wait || startedRef.current) return;
    startedRef.current = true;
    void begin();
  }, [begin, wait]);

  return { state, submit, retry };
}
