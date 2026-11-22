/** @type {import('tailwindcss').Config} */
// The tokens here are the shadcn/ui variable names, but their VALUES are the
// SENSEE-I foundations from docs/context/design-system.md. Colours are defined
// as CSS variables in src/index.css and referenced here, which is the shadcn
// convention and what lets components read `bg-primary`, `text-muted-foreground`
// and so on.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          hover: "hsl(var(--primary-hover))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        // The faintest legible tier: placeholder text and decorative chevrons.
        placeholder: "hsl(var(--placeholder))",
        // Body text sitting on a muted or tinted fill.
        body: "hsl(var(--body))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // The soft, non-punitive failure treatment from the design system.
        fail: {
          DEFAULT: "hsl(var(--fail))",
          border: "hsl(var(--fail-border))",
          foreground: "hsl(var(--fail-foreground))",
        },
        // The same treatment in the accent colour, for quiet green controls.
        "accent-soft": {
          DEFAULT: "hsl(var(--accent-soft))",
          border: "hsl(var(--accent-soft-border))",
          foreground: "hsl(var(--accent-soft-foreground))",
        },
        // The caution treatment, in the hat's yellow family.
        warn: {
          DEFAULT: "hsl(var(--warn))",
          border: "hsl(var(--warn-border))",
          foreground: "hsl(var(--warn-foreground))",
        },
        // The brand marks. Decorative only: never text under 24px, and never
        // a fill behind text. `primary` is what carries fills and green text.
        "brand-mint": "hsl(var(--brand-mint))",
        "brand-hat": "hsl(var(--brand-hat))",
      },
      borderRadius: {
        lg: "8px", // card radius
        md: "6px", // control radius
        sm: "4px",
      },
      fontFamily: {
        sans: ["Nunito", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      // Nunito runs lighter than Geist at the same weight, so the two weight
      // classes the design system uses are mapped up one step here rather
      // than at ~120 call sites. `font-medium` is 600 and `font-semibold`
      // is 700, which is why index.html loads 400, 600 and 700.
      fontWeight: {
        medium: "600",
        semibold: "700",
      },
      boxShadow: {
        raised: "0 1px 2px 0 rgba(0,0,0,0.05)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
