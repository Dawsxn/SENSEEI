/** Tick the classes a reading goes to. Used when uploading and when changing
 *  them later, so the two always read the same. With none ticked the reading is
 *  still saved, and the line underneath says what that means. */

import { useClasses } from "../classes/useClasses";

interface ClassPickerProps {
  selected: string[];
  onChange: (classIds: string[]) => void;
}

export function ClassPicker({ selected, onChange }: ClassPickerProps) {
  const { data: classes = [] } = useClasses();

  function toggle(id: string) {
    onChange(selected.includes(id) ? selected.filter((c) => c !== id) : [...selected, id]);
  }

  return (
    <div className="flex flex-col gap-2.5">
      {classes.map((c) => (
        <label key={c.id} className="flex w-fit cursor-pointer items-center gap-2.5 text-[14px]">
          <input
            type="checkbox"
            checked={selected.includes(c.id)}
            onChange={() => toggle(c.id)}
            className="h-4 w-4 cursor-pointer accent-[hsl(var(--primary))]"
          />
          {c.label}
        </label>
      ))}
      {selected.length === 0 && (
        <p className="text-[13px] text-muted-foreground">
          Students won&rsquo;t see this until you assign a class.
        </p>
      )}
    </div>
  );
}
