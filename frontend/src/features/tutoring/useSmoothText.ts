import { useEffect, useRef, useState } from "react";

/** Reveal `target` a little at a time, so streamed text types out smoothly.
 *
 * The model streams in chunks of uneven size and timing — a whole sentence,
 * then a pause, then two words — which reads as choppy if each chunk is painted
 * the instant it arrives. This decouples what is shown from what has arrived:
 * incoming text lands in `target`, and a rAF loop reveals it a fraction of the
 * remaining gap per frame, so display always chases the buffer at a steady,
 * self-pacing rate. When the stream ends (`done`), it flushes to the full text
 * at once rather than trailing behind.
 */
export function useSmoothText(target: string, done: boolean): string {
  const [shown, setShown] = useState("");
  const targetRef = useRef(target);
  targetRef.current = target;

  useEffect(() => {
    if (done) {
      setShown(targetRef.current);
      return;
    }
    let raf = 0;
    const tick = () => {
      setShown((prev) => {
        const full = targetRef.current;
        if (prev.length >= full.length) return prev;
        // Reveal ~1/6 of the outstanding gap each frame, at least one character,
        // so a large burst catches up fast and a trickle still advances.
        const step = Math.max(1, Math.ceil((full.length - prev.length) / 6));
        return full.slice(0, prev.length + step);
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [done]);

  // Before the first frame, show nothing rather than a flash of full text.
  return done ? target : shown;
}
