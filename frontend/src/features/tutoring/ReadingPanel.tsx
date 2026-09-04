/** The reading, shown for the whole session on the left of the split screen.
 *
 * Just the text. The title is in the top bar, and the core components are
 * deliberately not shown here: they are the instructor's model answer, so
 * putting them beside the chat would hand the student the very thing State asks
 * them to produce. Reading content is the one place body type goes above 14px:
 * 15px at 1.75 line height, per the design system. */

interface ReadingPanelProps {
  content: string;
}

export function ReadingPanel({ content }: ReadingPanelProps) {
  return (
    <div className="h-full overflow-y-auto lg:border-r">
      <article className="mx-auto max-w-[72ch] whitespace-pre-line px-5 py-6 text-[15px] leading-[1.75] text-[#3f3f46] sm:px-6">
        {content}
      </article>
    </div>
  );
}
