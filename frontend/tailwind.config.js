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
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
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
      },
      borderRadius: {
        lg: "8px", // card radius
        md: "6px", // control radius
        sm: "4px",
      },
      fontFamily: {
        sans: ["Geist", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        raised: "0 1px 2px 0 rgba(0,0,0,0.05)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
