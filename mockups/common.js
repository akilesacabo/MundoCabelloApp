// Shared loader for every mockup screen.
// Loaded with NO `defer` (synchronously) so the order in <head> is:
//   <script src="common.js"></script>   ← this file
//   <script src="tokens.js"></script>   ← sets tailwind.config AFTER
//   <link rel="stylesheet" href="tokens.css">  (added dynamically)
//
// This file adds:
//   1) Google Fonts (Inter / Montserrat / Material Symbols).
//   2) The shared CSS (typography + brutalist shadows).
// We intentionally do NOT inject the Tailwind CDN here — the HTML
// inlines its <script src="...cdn.tailwindcss.com"></script> tag
// directly so the CDN can register its config hook before any other
// script runs.
(function () {
  const fontHrefs = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@600;700;900&display=swap",
    "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap",
  ];
  fontHrefs.forEach((href) => {
    const l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    document.head.appendChild(l);
  });

  // Shared CSS (typography + brutalist shadows). Loaded with the
  // relative path that works when this file is in mockups/.
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = "tokens.css";
  document.head.appendChild(css);
})();

