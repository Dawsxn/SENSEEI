/** A chatbot reply, formatted the way a general-purpose chatbot shows one.
 *
 * The model writes Markdown. This reads the part of it a chat reply uses:
 * paragraphs, bulleted and numbered lists, headings, tables, dividers, bold,
 * italics and inline code. Everything else stays as plain text, and so does a
 * table that isn't well formed (a header row, then a |---| row). It builds React elements rather
 * than HTML, so nothing in a reply can run as markup. */

import { Fragment, type ReactNode } from "react";

type Block =
  | { kind: "p"; lines: string[] }
  | { kind: "h"; text: string }
  | { kind: "ul" | "ol"; items: string[] }
  | { kind: "code"; lines: string[] }
  | { kind: "table"; head: string[]; rows: string[][] }
  | { kind: "hr" };

const BULLET = /^\s*[-*+]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;
const RULE = /^\s*(-{3,}|\*{3,}|_{3,})\s*$/;
/** A table's second row: |---|:---:|---:| */
const TABLE_SEPARATOR = /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/;

/** A table row's cells: the outer pipes dropped, split on the rest. */
function cells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

/** Lines that all start with a pipe: a table if the second is a separator,
 *  otherwise a plain paragraph, exactly as written. */
function pipeBlock(lines: string[]): Block {
  if (lines.length >= 2 && TABLE_SEPARATOR.test(lines[1])) {
    const head = cells(lines[0]);
    const rows = lines
      .slice(2)
      .map(cells)
      // Every row as wide as the header, however the model wrote it.
      .map((row) => head.map((_, i) => row[i] ?? ""));
    return { kind: "table", head, rows };
  }
  return { kind: "p", lines };
}

export function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let fence: string[] | null = null;
  let pipes: string[] = [];
  const flushPipes = () => {
    if (pipes.length) blocks.push(pipeBlock(pipes));
    pipes = [];
  };
  for (const line of text.split("\n")) {
    if (!fence && line.trim().startsWith("|")) {
      pipes.push(line);
      continue;
    }
    flushPipes();
    if (line.trim().startsWith("```")) {
      if (fence) {
        blocks.push({ kind: "code", lines: fence });
        fence = null;
      } else {
        fence = [];
      }
      continue;
    }
    if (fence) {
      fence.push(line);
      continue;
    }
    const last = blocks[blocks.length - 1];
    const bullet = BULLET.exec(line);
    const numbered = NUMBERED.exec(line);
    const heading = HEADING.exec(line);
    if (!line.trim()) {
      blocks.push({ kind: "p", lines: [] }); // a break; empty ones are dropped below
    } else if (RULE.test(line)) {
      blocks.push({ kind: "hr" });
    } else if (heading) {
      blocks.push({ kind: "h", text: heading[1] });
    } else if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      const item = (bullet ?? numbered)![1];
      if (last && last.kind === kind) last.items.push(item);
      else blocks.push({ kind, items: [item] });
    } else if (last && last.kind === "p" && last.lines.length) {
      last.lines.push(line);
    } else {
      blocks.push({ kind: "p", lines: [line] });
    }
  }
  flushPipes();
  if (fence) blocks.push({ kind: "code", lines: fence });
  return blocks.filter((b) => b.kind !== "p" || b.lines.length > 0);
}

/** Bold, italics and inline code inside one line. */
export function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g;
  let at = 0;
  for (const match of text.matchAll(pattern)) {
    const i = match.index ?? 0;
    if (i > at) out.push(text.slice(at, i));
    const token = match[0];
    if (token.startsWith("**") || token.startsWith("__")) {
      out.push(<strong key={i}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      out.push(
        <code key={i} className="rounded bg-muted px-1 py-0.5 font-mono text-[13px]">
          {token.slice(1, -1)}
        </code>,
      );
    } else {
      out.push(<em key={i}>{token.slice(1, -1)}</em>);
    }
    at = i + token.length;
  }
  if (at < text.length) out.push(text.slice(at));
  return out;
}

export function ChatText({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-2.5 text-[14px] leading-relaxed">
      {parseBlocks(text).map((block, i) => {
        switch (block.kind) {
          case "h":
            return (
              <p key={i} className="font-semibold">
                {inline(block.text)}
              </p>
            );
          case "ul":
          case "ol": {
            const List = block.kind;
            return (
              <List
                key={i}
                className={`flex flex-col gap-1.5 pl-5 ${block.kind === "ul" ? "list-disc" : "list-decimal"} marker:text-muted-foreground`}
              >
                {block.items.map((item, j) => (
                  <li key={j}>{inline(item)}</li>
                ))}
              </List>
            );
          }
          case "table":
            // Scrolls sideways inside the reply on a narrow screen, so the page
            // itself never does.
            return (
              <div key={i} className="max-w-full overflow-x-auto">
                <table className="border-collapse text-[13px] leading-snug">
                  <thead>
                    <tr>
                      {block.head.map((cell, j) => (
                        <th key={j} className="border bg-muted px-2.5 py-1.5 text-left font-semibold">
                          {inline(cell)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {block.rows.map((row, r) => (
                      <tr key={r}>
                        {row.map((cell, j) => (
                          <td key={j} className="border px-2.5 py-1.5 align-top">
                            {inline(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case "hr":
            return <hr key={i} className="border-border" />;
          case "code":
            return (
              <pre key={i} className="overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-[13px]">
                {block.lines.join("\n")}
              </pre>
            );
          default:
            return (
              <p key={i}>
                {block.lines.map((line, j) => (
                  <Fragment key={j}>
                    {j > 0 && <br />}
                    {inline(line)}
                  </Fragment>
                ))}
              </p>
            );
        }
      })}
    </div>
  );
}
