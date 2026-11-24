/** The colours a student can give a class card, and where the choice is kept.
 *
 * The choice is kept in this browser only. It is a preference about how a page
 * looks, so losing it (another device, cleared site data) costs nothing but the
 * default colour back. */

export const CLASS_COLOURS = [
  { name: "Green", value: "#86efac" },
  { name: "Blue", value: "#93c5fd" },
  { name: "Yellow", value: "#fcd34d" },
  { name: "Pink", value: "#f9a8d4" },
  { name: "Purple", value: "#c4b5fd" },
] as const;

const key = (classId: string) => `senseei.class-colour.${classId}`;

/** The class's chosen colour, or the default for its place in the list, so
 *  side-by-side cards differ before anyone picks. */
export function classColour(classId: string, index: number): string {
  try {
    const saved = localStorage.getItem(key(classId));
    if (saved && CLASS_COLOURS.some((c) => c.value === saved)) return saved;
  } catch {
    // storage blocked; fall through to the default
  }
  return CLASS_COLOURS[index % CLASS_COLOURS.length].value;
}

export function saveClassColour(classId: string, value: string): void {
  try {
    localStorage.setItem(key(classId), value);
  } catch {
    // storage blocked; the colour holds until the page is left
  }
}
