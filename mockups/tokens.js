// Shared Tailwind theme for every mockup screen.
// Loaded with NO `defer` so it runs synchronously in <head> AFTER the
// Tailwind CDN <script>. The CDN reads the global `tailwind.config`
// assignment during initialization, which is why the assignment must
// use a plain `var` (a global property on `window`/`globalThis`).
//
// Two consumers:
//   1) The mockup HTMLs (loaded via <script src="tokens.js"></script>
//      immediately after <script src="common.js"></script> in <head>).
//   2) The frontend (React + Vite) will mirror this theme in
//      tailwind.config.ts to keep the production UI visually identical
//      to these static mockups.

var tailwind = window.tailwind || {};
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "on-surface": "#1f1b11",
        "primary-fixed": "#ffe08b",
        "inverse-on-surface": "#f9f0de",
        "on-tertiary-fixed-variant": "#454748",
        "on-tertiary-container": "#545657",
        "surface-container-highest": "#ebe1d1",
        "on-primary-fixed-variant": "#584400",
        "error": "#ba1a1a",
        "on-secondary-fixed": "#1b1b1b",
        "on-secondary-fixed-variant": "#474747",
        "inverse-surface": "#353025",
        "on-surface-variant": "#4e4633",
        "on-background": "#1f1b11",
        "error-container": "#ffdad6",
        "surface-bright": "#fff8f1",
        "on-error": "#ffffff",
        "on-primary": "#ffffff",
        "tertiary-container": "#cacbcc",
        "secondary-fixed-dim": "#c6c6c6",
        "tertiary-fixed-dim": "#c6c6c7",
        "tertiary-fixed": "#e2e2e3",
        "surface": "#fff8f1",
        "on-secondary-container": "#646464",
        "outline-variant": "#d1c5ac",
        "surface-dim": "#e2d9c8",
        "primary-fixed-dim": "#f0c110",
        "secondary-container": "#e2e2e2",
        "secondary": "#5e5e5e",
        "surface-variant": "#ebe1d1",
        "surface-container-low": "#fcf3e1",
        "on-tertiary-fixed": "#1a1c1d",
        "surface-container-lowest": "#ffffff",
        "secondary-fixed": "#e2e2e2",
        "surface-container": "#f6eddc",
        "on-tertiary": "#ffffff",
        "on-primary-fixed": "#241a00",
        "outline": "#807660",
        "inverse-primary": "#f0c110",
        "on-error-container": "#93000a",
        "on-secondary": "#ffffff",
        "primary-container": "#f5c518",
        "primary": "#745b00",
        "surface-tint": "#745b00",
        "surface-container-high": "#f1e7d6",
        "on-primary-container": "#695200",
        "tertiary": "#5d5e60",
        "background": "#fff8f1",
      },
      borderRadius: {
        DEFAULT: "0.125rem",
        lg: "0.25rem",
        xl: "0.5rem",
        full: "9999px",
      },
      spacing: {
        gutter: "16px",
        "stack-lg": "24px",
        "stack-sm": "4px",
        "stack-md": "12px",
        base: "8px",
        "section-gap": "48px",
        "container-margin": "24px",
      },
      fontFamily: {
        "headline-lg-mobile": ["Montserrat", "sans-serif"],
        "label-sm": ["Inter", "sans-serif"],
        "body-md": ["Inter", "sans-serif"],
        "headline-lg": ["Montserrat", "sans-serif"],
        "label-md": ["Inter", "sans-serif"],
        "headline-md": ["Montserrat", "sans-serif"],
        "display-lg": ["Montserrat", "sans-serif"],
        "body-lg": ["Inter", "sans-serif"],
      },
      fontSize: {
        "headline-lg-mobile": ["24px", { lineHeight: "32px", fontWeight: "700" }],
        "label-sm": ["12px", { lineHeight: "16px", fontWeight: "500" }],
        "body-md": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "headline-lg": ["32px", { lineHeight: "40px", fontWeight: "700" }],
        "label-md": [
          "14px",
          { lineHeight: "20px", letterSpacing: "0.05em", fontWeight: "600" },
        ],
        "headline-md": ["20px", { lineHeight: "28px", fontWeight: "600" }],
        "display-lg": [
          "48px",
          { lineHeight: "56px", letterSpacing: "-0.02em", fontWeight: "700" },
        ],
        "body-lg": ["18px", { lineHeight: "28px", fontWeight: "400" }],
      },
    },
  },
};
