/** The control groups' pieces: how a chatbot reply is formatted, how the
 *  conversation's state moves, and what the event log keeps. */

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ChatText, parseBlocks } from "./ChatText";
import { __queue, logTrial, setTrialContext } from "./trialLog";
import { initialChat, reduceChat } from "./useChatbot";

describe("a chatbot reply", () => {
  it("reads paragraphs, lists and headings", () => {
    const blocks = parseBlocks(
      "## Offloading\n\nIt means:\n\n- writing a list\n- setting an alarm\n\n1. first\n2. second\nLast line.",
    );
    expect(blocks.map((b) => b.kind)).toEqual(["h", "p", "ul", "ol", "p"]);
  });

  it("shows bold and code, and never runs markup", () => {
    render(<ChatText text={"A **key** idea, `x = 1`, and <img src=x onerror=alert(1)>"} />);
    expect(screen.getByText("key").tagName).toBe("STRONG");
    expect(screen.getByText("x = 1").tagName).toBe("CODE");
    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x/)).toBeInTheDocument();
  });
});

describe("the conversation", () => {
  it("streams a reply into place", () => {
    let s = reduceChat(initialChat, { type: "loaded", rows: [] });
    s = reduceChat(s, { type: "send", text: "Hi" });
    s = reduceChat(s, { type: "event", event: { type: "delta", text: "Hel" } });
    s = reduceChat(s, { type: "event", event: { type: "delta", text: "lo" } });
    expect(s.lines.map((l) => [l.role, l.content, l.streaming])).toEqual([
      ["user", "Hi", false],
      ["assistant", "Hello", true],
    ]);
    s = reduceChat(s, { type: "event", event: { type: "message_end", id: "m2", content: "Hello." } });
    expect(s.phase).toBe("ready");
    expect(s.lines[1]).toMatchObject({ content: "Hello.", streaming: false });
  });

  it("drops the empty reply when sending fails, and keeps the question", () => {
    let s = reduceChat(reduceChat(initialChat, { type: "loaded", rows: [] }), { type: "send", text: "Hi" });
    s = reduceChat(s, { type: "event", event: { type: "error", detail: "time is up" } });
    expect(s.lines.map((l) => l.role)).toEqual(["user"]);
    expect(s.phase).toBe("error");
  });

  it("picks up where it was after a reload", () => {
    const s = reduceChat(initialChat, {
      type: "loaded",
      rows: [
        { id: "1", role: "user", content: "Q", created_at: "" },
        { id: "2", role: "assistant", content: "A", created_at: "" },
      ],
    });
    expect(s.lines.map((l) => l.content)).toEqual(["Q", "A"]);
    expect(s.phase).toBe("ready");
  });
});

describe("the event log", () => {
  afterEach(() => __queue.reset());

  it("keeps nothing unless a participant's screen switched it on", () => {
    logTrial("tab_left");
    expect(__queue.peek()).toEqual([]);
  });

  it("records a paste as its length, with the time it happened", () => {
    __queue.enable();
    logTrial("paste", { length: 412 });
    const [event] = __queue.peek();
    expect(event.kind).toBe("paste");
    expect(event.data).toEqual({ length: 412 });
    expect(Date.now() - Date.parse(event.at)).toBeLessThan(5000);
  });

  it("stamps each event with the SEE-I step and attempt it happened on", () => {
    __queue.enable();
    setTrialContext({ step: "Elaborate", attempt: 2 });
    logTrial("panel_opened", { panel: "rubric" });
    setTrialContext({});
    logTrial("tab_left");
    const [panel, tab] = __queue.peek();
    expect(panel.data).toEqual({ panel: "rubric", step: "Elaborate", attempt: 2 });
    expect(tab.data).toBeUndefined();
  });
});
