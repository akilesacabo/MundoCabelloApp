// v2 "Soft Luxe" — Tailwind theme + shared helpers.
// Loaded synchronously in <head> right after the Tailwind CDN <script>.
var tailwind = window.tailwind || {};
tailwind.config = {
  theme: {
    extend: {
      colors: {
        ink: "#2a2130",
        muted: "#7c6f83",
        line: "#efe6ef",
        brand: {
          50: "#fbf1f8", 100: "#f6e0ef", 200: "#eec2df",
          300: "#e29ac9", 400: "#d46fb0", 500: "#c14f98",
          600: "#a63a80", 700: "#872f68", 800: "#6f2955", 900: "#5b2447",
        },
        gold: { 400: "#e6b45a", 500: "#d69b3d", 600: "#b97f28" },
        cream: "#fdf8f5",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["'Plus Jakarta Sans'", "sans-serif"],
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgba(90, 40, 80, 0.18)",
        card: "0 18px 50px -20px rgba(90, 40, 80, 0.28)",
        glow: "0 8px 24px -6px rgba(193, 79, 152, 0.45)",
      },
      borderRadius: { xl2: "1.25rem", xl3: "1.75rem" },
    },
  },
};

// Area palette for v2 (softer / more modern than v1)
window.V2 = {
  areaColor: {
    peluqueria: "#e26fae",
    hidratacion: "#4bb6e8",
    manicure: "#e6a93d",
    cejas: "#4fbf8f",
  },
  areaSoft: {
    peluqueria: "#fbe8f3",
    hidratacion: "#e2f3fb",
    manicure: "#fbf1dd",
    cejas: "#e2f6ee",
  },
  statusColor: {
    DISPONIBLE: "#4fbf8f",
    OCUPADO: "#e26fae",
    BREAK: "#e6a93d",
  },
  titleCase(s) {
    return String(s).toLowerCase().trim().split(/\s+/)
      .map(w => (w ? w[0].toUpperCase() + w.slice(1) : w)).join(" ");
  },
  escape(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  },
  minsAgo(ts) {
    const m = Math.max(0, Math.round((Date.now() - ts) / 60000));
    return m === 0 ? "recién" : `hace ${m} min`;
  },
};
