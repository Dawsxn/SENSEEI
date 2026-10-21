/** A chatbot reply, formatted the way a general-purpose chatbot shows one.
 *
 * The model writes Markdown. This reads the part of it a chat reply uses:
 * paragraphs, bulleted and numbered lists, headings, bold, italics and inline
 * code. Everything else stays as plain text. It builds React elements rather
 * than HTML, so nothing in a reply can run as markup. */

import { Fragment, type ReactNode } from "react";

type Block =
  | { kind: "p"; lines: string[] }
  | { kind: "h"; text: string }
  | { kind: "ul" | "ol"; items: string[] }
  | { kind: "code"; lines: string[] };

const BULLET = /^\s*[-*+]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;

export function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let fence: string[] | null = null;
  for (const line of text.split("\n")) {
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
