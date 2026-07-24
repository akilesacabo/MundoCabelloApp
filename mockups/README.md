# Mockups — El Mundo del Cabello (Fase 1)

Cuatro pantallas de referencia visual, extraídas del export de Stitch
(`../Pantallas para demo de peluqueria.html`) y servidas como HTML
estático navegable. Sirven como spec visual durante el desarrollo del
MVP.

## Estructura

```
mockups/
├── 01-confirmacion.html   # Splash: número de turno + volver al inicio
├── 02-panel.html          # Cola + grid de personal + acciones
├── 03-checkin.html        # Formulario de 5 campos + servicios
├── 04-staff.html          # Directorio de profesionales
├── common.js              # Loader compartido (fonts + tailwind + CSS)
├── tokens.js              # Tailwind config compartida
└── tokens.css             # Tipografía + sombras brutalistas
```

`../index.html` es el hub con links a las 4 pantallas.

## Cómo abrir

Los mockups cargan Tailwind y las Google Fonts desde CDN, así que
necesitan conexión a internet. Basta con servir la carpeta por HTTP
para que `common.js` resuelva `tokens.css` correctamente:

```bash
cd .. && python3 -m http.server 5173
# luego abrir http://localhost:5173/
```

Si abres los `.html` directamente con `file://`, `common.js` se cargará
pero `tokens.css` puede fallar por políticas de CORS locales — usar el
servidor HTTP es lo recomendado.

## Convenciones

- **Identidad visual:** paleta blanco / amarillo (#F5C518) / negro,
  fuente Inter + Montserrat, Material Symbols, sombras brutalistas
  (`box-shadow: 4px 4px 0 #000`).
- **Cada pantalla es self-contained** salvo por los assets compartidos.
  El nav inyectado en la esquina superior izquierda permite saltar
  entre las 4 pantallas y volver al hub.
- Las clases `text-headline-lg`, `font-headline-lg`, `bg-primary-container`,
  `shadow-brutal`, etc. vienen de la config compartida en `tokens.js` y
  deben replicarse 1:1 en el `tailwind.config.ts` del frontend React
  cuando lo construyamos.
