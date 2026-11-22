/** The SENSEE-I logo, from `public/brand/`.
 *
 * The mark's font is already outlined inside the SVG, so nothing here depends
 * on a webfont being loaded; UI text stays in Nunito. `white` is the variant
 * for a dark or coloured ground. The default height fits the 56px top bar. */
export function Logo({
  variant = "colour",
  className = "h-7 w-auto",
}: {
  variant?: "colour" | "white";
  className?: string;
}) {
  return (
    <img
      src={`/brand/sensee-i-logo${variant === "white" ? "-white" : ""}.svg`}
      alt="SENSEE-I"
      className={className}
      draggable={false}
    />
  );
}
