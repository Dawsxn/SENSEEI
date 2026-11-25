/** Tick the classes a reading goes to. Used when uploading and when changing
 *  them later, so the two always read the same. With none ticked the reading is
 *  still saved; the line above the picker says who can open it. */

import { cn } from "../../lib/utils";
import { useClasses } from "../classes/useClasses";

interface ClassPickerProps {
  selected: string[];
  onChange: (classIds: string[]) => void;
}

export function ClassPicker({ selected, onChange }: ClassPickerProps) {
  const { data: classes, isLoading } = useClasses();

  function toggle(id: string) {
    onChange(selected.includes(id) ? selected.filter((c) => c !== id) : [...selected, id]);
  }

  if (isLoading) return null;
  if (!classes?.length) {
    return <p className="text-[14px] text-muted-foreground">No classes available</p>;
  }
  return (
    <div className="overflow-hidden rounded-lg border">
      {classes.map((c, i) => (
        <label
          key={c.id}
          className={cn("flex cursor-pointer items-center gap-2.5 px-3.5 py-3 text-[14px] hover:bg-muted/50", i > 0 && "border-t")}
        >
          <input
            type="checkbox"
            checked={selected.includes(c.id)}
            onChange={() => toggle(c.id)}
            className="h-4 w-4 cursor-pointer accent-[hsl(var(--primary))]"
          />
          {c.label}
        </label>
      ))}
    </div>
  );
}
