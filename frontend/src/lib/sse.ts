/**
 * Reading Server-Sent Events from a `fetch` response.
 *
 * The tutoring turns are POSTs (they send the student's answer as a body), and
 * the browser's built-in `EventSource` only does GET. So the stream is read
 * manually: `fetch` gives a byte stream, and this parses the `event:` / `data:`
 * frames out of it.
 *
 * The one thing that must be right is buffering across chunk boundaries. A
 * `read()` returns whatever bytes have arrived, which need not line up with SSE
 * frame boundaries — a single `data:` line can be split across two reads, and
 * two frames can arrive in one. The parser therefore accumulates into a buffer
 * and only emits a frame once it has seen the blank line that terminates it.
 * `parseSSEChunks` takes any async iterable of byte chunks precisely so a test
 * can feed it deliberately awkward splits.
 */

export interface SSEEvent {
  /** The `event:` name, or "message" when a frame omits it (the SSE default). */
  event: string;
  /** The joined `data:` lines, still a string; the caller JSON-parses it. */
  data: string;
}

/** Parse one frame (the text between blank lines) into an event, or null. */
function parseFrame(raw: string): SSEEvent | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (line === "" || line.startsWith(":")) continue; // blank or comment
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    // A single leading space after the colon is stripped, per the SSE spec.
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") event = value;
    else if (field === "data") dataLines.push(value);
  }

  if (dataLines.length === 0) return null; // a frame with no data is not an event
  return { event, data: dataLines.join("\n") };
}

/** Parse SSE frames out of a stream of byte chunks. */
export async function* parseSSEChunks(
  source: AsyncIterable<Uint8Array>,
): AsyncGenerator<SSEEvent> {
  const decoder = new TextDecoder();
  let buffer = "";

  for await (const chunk of source) {
    buffer += decoder.decode(chunk, { stream: true });

    // Frames are separated by a blank line. Normalise CRLF so either works.
    let sep = findSeparator(buffer);
    while (sep !== -1) {
      const frame = buffer.slice(0, sep.index);
      buffer = buffer.slice(sep.index + sep.length);
      const event = parseFrame(frame);
      if (event) yield event;
      sep = findSeparator(buffer);
    }
  }

  // A final frame with no trailing blank line is still worth emitting.
  const tail = parseFrame(buffer);
  if (tail) yield tail;
}

/** The first frame separator (\n\n or \r\n\r\n) in the buffer, or -1. */
function findSeparator(buffer: string): { index: number; length: number } | -1 {
  const lf = buffer.indexOf("\n\n");
  const crlf = buffer.indexOf("\r\n\r\n");
  if (lf === -1 && crlf === -1) return -1;
  if (crlf === -1 || (lf !== -1 && lf < crlf)) return { index: lf, length: 2 };
  return { index: crlf, length: 4 };
}

/** Adapt a fetch `Response` body to the async iterable the parser reads. */
export async function* readSSE(response: Response): AsyncGenerator<SSEEvent> {
  if (!response.body) throw new Error("response has no body to stream");
  const reader = response.body.getReader();
  try {
    yield* parseSSEChunks({
      async *[Symbol.asyncIterator]() {
        while (true) {
          const { done, value } = await reader.read();
          if (done) return;
          if (value) yield value;
        }
      },
    });
  } finally {
    reader.releaseLock();
  }
}
