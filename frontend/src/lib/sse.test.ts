import { describe, expect, it } from "vitest";

import { parseSSEChunks, type SSEEvent } from "./sse";

const encoder = new TextEncoder();

/** Feed the parser a fixed list of string chunks, exactly as split. */
async function collect(chunks: string[]): Promise<SSEEvent[]> {
  async function* source() {
    for (const c of chunks) yield encoder.encode(c);
  }
  const out: SSEEvent[] = [];
  for await (const ev of parseSSEChunks(source())) out.push(ev);
  return out;
}

describe("parseSSEChunks", () => {
  it("parses a single well-formed frame", async () => {
    const events = await collect(["event: delta\ndata: hello\n\n"]);
    expect(events).toEqual([{ event: "delta", data: "hello" }]);
  });

  it("parses several frames in one chunk", async () => {
    const events = await collect([
      "event: delta\ndata: a\n\nevent: delta\ndata: b\n\n",
    ]);
    expect(events.map((e) => e.data)).toEqual(["a", "b"]);
  });

  it("reassembles a frame split across chunks", async () => {
    // the split lands in the middle of the data value
    const events = await collect(["event: delta\ndata: hel", "lo\n\n"]);
    expect(events).toEqual([{ event: "delta", data: "hello" }]);
  });

  it("reassembles when the blank-line separator itself is split", async () => {
    const events = await collect(["event: delta\ndata: hi\n", "\nevent: state\ndata: {}\n\n"]);
    expect(events).toEqual([
      { event: "delta", data: "hi" },
      { event: "state", data: "{}" },
    ]);
  });

  it("emits one delta per byte-chunk when the model streams token by token", async () => {
    const events = await collect([
      "event: delta\ndata: That\n\n",
      "event: delta\ndata:  attempt\n\n",
      "event: delta\ndata:  drifts\n\n",
    ]);
    expect(events.map((e) => e.data).join("")).toBe("That attempt drifts");
  });

  it("keeps a leading space in data beyond the one the spec strips", async () => {
    // "data:  attempt" → spec strips one space → " attempt"
    const events = await collect(["event: delta\ndata:  attempt\n\n"]);
    expect(events[0].data).toBe(" attempt");
  });

  it("defaults the event name to 'message' when omitted", async () => {
    const events = await collect(["data: bare\n\n"]);
    expect(events[0]).toEqual({ event: "message", data: "bare" });
  });

  it("carries JSON payloads through untouched for the caller to parse", async () => {
    const payload = JSON.stringify({ status: "in_progress", attempts_left: 2 });
    const events = await collect([`event: state\ndata: ${payload}\n\n`]);
    expect(JSON.parse(events[0].data)).toEqual({
      status: "in_progress",
      attempts_left: 2,
    });
  });

  it("emits a trailing frame with no final blank line", async () => {
    const events = await collect(["event: state\ndata: {}"]);
    expect(events).toEqual([{ event: "state", data: "{}" }]);
  });

  it("ignores comments and blank keep-alive lines", async () => {
    const events = await collect([": keep-alive\n\nevent: delta\ndata: x\n\n"]);
    expect(events).toEqual([{ event: "delta", data: "x" }]);
  });

  it("handles CRLF line endings", async () => {
    const events = await collect(["event: delta\r\ndata: hello\r\n\r\n"]);
    expect(events).toEqual([{ event: "delta", data: "hello" }]);
  });
});
