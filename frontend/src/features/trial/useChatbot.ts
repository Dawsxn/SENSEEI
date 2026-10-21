/** The chatbot group's conversation as React state.
 *
 * It loads what was said before, so a reload picks the conversation back up,
 * then streams each reply in as it arrives. `reduce` is pure, like the tutoring
 * session's, so the turn-by-turn behaviour is testable without a network. */

import { useCallback, useEffect, useReducer, useRef } from "react";

import { getChat, sendChat } from "../../lib/api";
import { logTrial } from "./trialLog";
import type { ChatEvent, ChatMessageRow } from "./types";

export interface ChatLine {
  key: string;
  role: "user" | "assistant";
  content: string;
  streaming: boolean;
}

export interface ChatState {
  lines: ChatLine[];
  phase: "loading" | "ready" | "streaming" | "error";
  error: string | null;
  seq: number;
}

export const initialChat: ChatState = { lines: [], phase: "loading", error: null, seq: 0 };

export type ChatAction =
  | { type: "loaded"; rows: ChatMessageRow[] }
  | { type: "send"; text: string }
  | { type: "event"; event: ChatEvent };

export function reduceChat(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "loaded":
      return {
        ...state,
        phase: "ready",
        lines: action.rows.map((r) => ({
          key: r.id,
          role: r.role,
          content: r.content,
          streaming: false,
        })),
      };
    case "send":
      return {
        ...state,
        phase: "streaming",
        error: null,
        seq: state.seq + 2,
        lines: [
          ...state.lines,
          { key: `u${state.seq}`, role: "user", content: action.text, streaming: false },
          { key: `a${state.seq}`, role: "assistant", content: "", streaming: true },
        ],
      };
    case "event":
      return applyChatEvent(state, action.event);
  }
}

function applyChatEvent(state: ChatState, event: ChatEvent): ChatState {
  const lines = state.lines.slice();
  const last = lines[lines.length - 1];
  switch (event.type) {
    case "message_start":
      return state;
    case "delta":
      if (last?.streaming) lines[lines.length - 1] = { ...last, content: last.content + event.text };
      return { ...state, lines };
    case "message_end":
      if (last?.streaming) lines[lines.length - 1] = { ...last, content: event.content, streaming: false };
      return { ...state, lines, phase: "ready" };
    case "error":
      // A reply that never came leaves no empty bubble behind.
      if (last?.streaming) lines.pop();
      return { ...state, lines, phase: "error", error: event.detail };
  }
}

export function useChatbot(enabled: boolean) {
  const [state, dispatch] = useReducer(reduceChat, initialChat);
  const loaded = useRef(false);

  useEffect(() => {
    if (!enabled || loaded.current) return;
    loaded.current = true;
    getChat()
      .then((rows) => dispatch({ type: "loaded", rows }))
      .catch(() => dispatch({ type: "loaded", rows: [] }));
  }, [enabled]);

  const send = useCallback(async (text: string) => {
    dispatch({ type: "send", text });
    for await (const event of sendChat(text)) {
      dispatch({ type: "event", event });
      if (event.type === "message_end") logTrial("reply_shown");
    }
  }, []);

  return { state, send };
}
