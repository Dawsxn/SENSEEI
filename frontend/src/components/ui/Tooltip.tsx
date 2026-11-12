/** A tooltip in the app's own clothes, and the little "what is this?" mark that
 *  uses it.
 *
 * Ours rather than the browser's, whose black box belongs to no theme and
 * cannot be styled. The bubble is the same card the rest of the app is built
 * from: white surface, one-pixel border, soft shadow.
 *
 * CSS only, no library and no state: hovering or focusing what it wraps shows
 * the bubble. The bubble ignores the pointer, so it can never sit between the
 * cursor and a click, and it is hidden with `display: none` rather than
 * opacity, because an invisible box still counts towards the page's width and a
 * bubble hanging off the last card in a row was enough to give the whole page a
 * horizontal scrollbar.
 *
 * A button whose label is only an icon carries its name here and in
 * `aria-label`: one for people who can see it, one for people who cannot.
 */

import { Info } from "lucide-react";

interface TooltipProps {
  text: string;
  /** Which side the bubble opens from. Right by default; `left` for a trigger
   *  near the right edge, where the bubble would run off. */
  align?: "left" | "right";
  children: React.ReactNode;
}

export function Tooltip({ text, align = "right", children }: TooltipProps) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span
        role="tooltip"
        className={`pointer-events-none absolute top-full z-20 mt-1.5 hidden w-max max-w-[230px] rounded-md border bg-background px-2.5 py-1.5 text-[12px] font-normal leading-snug text-muted-foreground shadow-lg group-focus-within:block group-hover:block ${
          align === "right" ? "left-0" : "right-0"
        }`}
      >
        {text}
      </span>
    </span>
  );
}

export function InfoTip({ text, align = "right" }: Omit<TooltipProps, "children">) {
  return (
    <Tooltip text={text} align={align}>
      <button
        type="button"
        aria-label={text}
        className="flex cursor-help items-center text-muted-foreground/70 hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
    </Tooltip>
  );
}
