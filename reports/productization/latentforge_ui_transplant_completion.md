# UI Transplant — LatentForge Design System

**Date:** 2026-09-12 (updated 2026-09-13: light theme flip; cozy journal restyle; Grainient visibility fix)
**Scope:** `product/frontend/` only. Zero backend changes, zero test changes, zero v1/source-tree changes.

## Update 5 — Grainient actually visible (paint-order fix) + scientific touches

**Root cause found:** the background color was set on `html`, `body`, AND `#root`. A `position: fixed; z-index: -1` layer paints behind in-flow block backgrounds in the same stacking context, so `<body>`'s opaque cream background was painted ON TOP of the Grainient layer — it was rendering the entire time, fully hidden. Opacity was never the issue.

1. **Fix:** background color now lives only on `<html>` (the canvas paints it first); `body`/`#root` are transparent. The fixed Grainient layer now shows through.
2. **Scientific styling:** the layer gained a graph-paper overlay (fine 24px rule grid + 192px major lines, warm brown alpha) — lab-notebook paper over the animated gradient. Grainient palette shifted to muted sage on cream (`#F6F1E7` / `#A9C9AF` / `#628F72`) with slower motion (`timeSpeed 0.15`, `warpSpeed 1.4`) and higher film grain (`0.12`) for an instrumented, measured feel.
3. **Figure labels:** Dashboard section labels now read as research figures — `Fig. 01 · Forecast evidence — locked test partition` through `Fig. 05 · Recent audit events` (no test contract touched).

### Update 5 verification (exact commands + outcomes)
- `npx vitest run` → **Test Files 5 passed (5), Tests 27 passed (27)**
- `npx tsc --noEmit` → exit 0
- `npm run build` → built in 4.38s
- Files touched: `styles.css` (base background rule, `.bg-grainient::after` grid), `App.tsx` (Grainient palette/motion), `pages/Dashboard.tsx` (Fig. labels)

## Update 6 — De-AI pass + working research console

**Design:** the now-visible background was far too loud (saturated green field) and, with the handwritten accents, read "AI-generated". Fixes: Grainient palette moved to near-paper tones (`#F6F1E7 / #DCE5D6 / #E7DEC9`, saturation 0.55, contrast 1.05, timeSpeed 0.12), hero glow down to .12, and the Caveat handwriting on card links / empty hints replaced with italic serif. The result sits closer to a restrained research-paper aesthetic: cream paper, serif headings, mono data, faint graph-paper grid.

**Working research console** (the "actual working dashboard" request): a new `Fig. 06 · Live research console` section on the Dashboard runs a real local experiment end-to-end.

Backend (`product/backend_api/app/routers/research.py`, wired into `main.py`):
- `POST /api/research/datasets` — CSV upload (32 MB cap, UTF-8), validated for a parsable timestamp column and numeric columns; stored under `artifacts/research_ui/datasets/<id>/` with a `manifest.json` recorded BEFORE first use (source, license, retrieval date, version sha256, schema, rows, range) per the dataset policy. `GET /datasets` lists them.
- `POST /api/research/runs` — real forecasting run: leakage-safe features (cyclic hour/dow/doy + lag 1/24/168; rows without full lag history dropped, never future-imputed), strict chronological holdout (configurable test fraction), Ridge / HistGradientBoosting via the frozen `models/classical.py` factories vs a seasonal-naive (lag-24) benchmark. Reports MAE/RMSE/improvement %, renewable-utilization ratios when wind/pv/solar + load columns exist (renewable share, load-matching ratio, surplus hours, correlation — all aggregated over ALL renewable columns, described honestly as "not a dispatch plan"), a sampled test-window series, and a persisted run JSON under `artifacts/research_ui/runs/`.
- Advisory output uses bounded recommendation types only (EXPLAIN / INVESTIGATE / CREATE_REPORT), is deterministic, and never suggests lifecycle actions; results are research evidence only and never bypass governance.
- Dependency added: `python-multipart` (CSV upload).

Frontend: `components/ResearchConsole.tsx` (3-step workflow: add dataset → run forecast → evidence with MAE/improvement/renewable-matching cards, canvas chart of actual vs predicted, advisory list), typed client methods incl. multipart upload, and CSS for the console. No nav items added and no test files changed (sidebar contract stays 8 links).

### Update 6 verification (exact commands + outcomes)
- Frontend: `npx vitest run` → **Tests 27 passed (27)**; `npx tsc --noEmit` → 0 errors; `npm run build` → OK
- Backend: `create_app().openapi()` lists `/api/research/datasets` + `/api/research/runs`
- Live end-to-end (synthetic 2880-row hourly CSV, load/wind/pv): upload registered `ui-1bc51b03df44` (manifest recorded); Ridge run → MAE 2.360 vs benchmark 3.346 (+29.5%); HGB run → MAE 2.747 (+17.9%); renewable share 62.5%, load-matching 56.5%, surplus 740 h, corr −0.379; advisory `[EXPLAIN, CREATE_REPORT]`; 272-point test series returned

## Update 4 — Cozy journal aesthetic + Grainient visibility

1. **Grainient visibility:** layer opacity `.5 → 1` and the static CSS fallback strengthened (two radial green washes at `.7/.6` alpha), so the animated background is clearly visible and something still shows if WebGL is unavailable.
2. **Cozy journal restyle** (original implementation; design tokens sampled from the reference site's public CSS — palette values and font stacks only, no markup/copy/assets copied):
   - Surfaces: warm cream paper — background `oklch(0.955 0.022 75)`, cards `oklch(0.985 0.012 75)`, alt surfaces `oklch(0.93–0.94 … 72)`.
   - Ink: warm brown (`oklch(0.24 0.035 60)` headings, `oklch(0.36 0.03 62)` body, warm muted `oklch(0.50 0.03 70)`); all black-alpha hairlines/hovers/shadows warmed to `oklch(0.25 0.04 60 / α)`.
   - Accent system: terracotta primary `oklch(0.585 0.16 42)` (filled pill buttons with soft warm shadow), leaf green `oklch(0.52 0.13 150)` for ok/connected, sky `oklch(0.52 0.10 235)` for info pills, sun amber for warnings, warm red destructive.
   - Typography: headings switched to a serif stack (ui-serif/Georgia/Iowan), body to system-ui, JetBrains Mono retained for data; Caveat 600/700 added and used for handwritten accents (card links, empty-state hints).
   - Shape/feel: radii bumped (`--radius` 12px, `--radius-lg` 20px), pill-shaped buttons, active nav/tab fills softened to terracotta tint `.13`, diffuse warm shadows replacing neon glows, OFFLINE EVALUATION badge moved to leaf-green tint.
3. **Grainient background kept green** — reads as a soft meadow wash under the cream theme; MaskedHeading hero fill unchanged (green gradient).

### Update 4 verification (exact commands + outcomes)
- `npx vitest run` → **Test Files 5 passed (5), Tests 27 passed (27)**
- `npx tsc --noEmit` → exit 0
- `npm run build` → built OK (chunk-size note unchanged, informational)
- Files touched: `styles.css`, `App.tsx` (Grainient opacity), `index.html` (fonts URL)

## Update 3 — Light theme (black → white background)

The dark theme was flipped to a light theme while keeping white primary + green secondary:

1. **Tokens:** `--background` → white `oklch(1 0 0)`, headings `--foreground` → near-black, `--text-body`/`--muted-foreground` → dark grays, surfaces inverted (`--surface-0/1` light), hairlines flipped to `oklch(0 0 0 / .08/.14)`, `color-scheme: light`. Green re-tuned for white backgrounds: text-accent green darkened to `oklch(0.52 0.16 152)`; tinted pill/panel backgrounds use light green washes. `--positive`/`--warning`/`--destructive` darkened for legibility on white.
2. **Hardcoded dark values swapped:** header backdrop (`oklch(1 0 0 / .82)` + blur), hero grid lines, ghost/secondary button backgrounds, table header tints and row hovers, code background, empty-state tint, active nav/tab inset rings, selection color — all moved from white-alpha-on-dark to black-alpha-on-light.
3. **White primary on white background:** primary and hero primary buttons gained a hairline border + subtle drop shadow so the white fill remains visible; hover keeps the green glow.
4. **Hero glow** opacity reduced to .22 (a strong green blob would be harsh on white).
5. **Grainient background** re-palette for light mode: `#FFFFFF` / `#A7F3D0` / `#F2FBF6` with `contrast 1.1`, layer opacity raised to .35 — a soft animated white-green wash on the white page.
6. **MaskedHeading fill** changed to a light→deep green gradient (`#4ADE80 → #15803D`) so the letters read against the white page.

### Update 3 verification (exact commands + outcomes)
- `npx vitest run` → **Tests 27 passed (27)**
- `npx tsc --noEmit` → exit 0
- `npm run build` → built in 4.64s (chunk-size note unchanged, informational)

## Update 2 — Recolor + React Bits integration

1. **Recolor (white primary, green secondary):** `--primary` → `oklch(1 0 0)` with black `--primary-foreground` (white buttons, dark text), `--primary-hover` → `oklch(0.92 0 0)`; secondary accent hue moved from teal 194° to green 152° (`--green: oklch(0.79 0.17 152)`) across all eyebrow/section labels, status pills, active-tab inset rings, focus rings, selection, card-hover borders, and the hero glow. Brand gradient is now white→green.
2. **`MaskedHeading` (React Bits, JS+CSS + gsap):** converted to TypeScript at `src/components/MaskedHeading.tsx` + `MaskedHeading.css`. Rendered as the Dashboard hero heading (`tag="h2"`, `reveal="rise"`, `trigger="view"`, `textScale={0.042}`, left-aligned), filled with a white→green data-URI SVG gradient. Guards added for jsdom: `matchMedia`, `ResizeObserver`, `IntersectionObserver`.
3. **`Grainient` (React Bits, JS+CSS + ogl):** converted to TypeScript at `src/components/Grainient.tsx` + `Grainient.css`. Mounted once in `App.tsx` as a fixed full-page background (`.bg-grainient`, `z-index: -1`, opacity .16, `pointer-events: none`) with palette white `#FFFFFF` / green `#22C55E` / deep green-black `#03130B`, tuned warp/grain/contrast. WebGL context creation is wrapped so headless/test environments render nothing instead of crashing.
4. **Dependencies:** `gsap`, `ogl` added to `product/frontend/package.json`.

### Update 2 verification (exact commands + outcomes)
- `npx vitest run` → **Test Files 5 passed (5), Tests 27 passed (27)** (initial run had 3 failures from jsdom's missing `window.matchMedia`; fixed with a guard and re-verified)
- `npx tsc --noEmit` → exit 0
- `npm run build` → built in 4.54s; JS 565.88 kB (gsap+ogl now bundled; Vite emits a >500 kB chunk-size note — informational only)
- Live: Vite (5173) returns 200 and hot-reloads; backend (8000) `/health` = `UP`

## Original transplant

## Request

Clone the UI design of the user's own site `https://latentforge.onrender.com/lab` (their repository) into this project's frontend console.

## What was transplanted

Design system extracted from the user's own LatentForge repository CSS (`tokens.css`, `site.css`, `lab.css`) and applied to the existing smart-grid console class names — no page restructure, no content changes, no test contract changes.

1. **Design tokens (verbatim from the user's repo):** full OKLCH palette (`--primary` blue `oklch(0.5683 0.2366 264.2478)`, teal `--chart-2`, hairlines at `oklch(1 0 0 / .08 / .14)`), brand gradient `linear-gradient(90deg, blue → teal)`, glow tokens (`--glow-primary`, `--glow-soft`), radii (6/10/16/pill), motion tokens (`--ease-out`, `--dur-fast`, `--dur`), `color-scheme: dark`.
2. **Layout:** the left sidebar became a **sticky top header** (LatentForge `site-header` pattern): translucent blurred backdrop (`oklch(0 0 0 / .78)` + `blur(16px) saturate(140%)`), brand mark + wordmark + `Lab` brand-tag, nav links as pills with accent-background active state, status badges right.
3. **Components restyled to the LatentForge look:**
   - Pills/badges: bordered pill + colored dot (`::before`), mono uppercase, tone variants with tinted borders/backgrounds (ok/warn/bad/info).
   - Cards: gradient surfaces `linear-gradient(180deg, surface-1, surface-0)`, hairline-strong border, `radius-lg`, hover glow `--glow-soft`.
   - Tables: bordered scroll container, mono uppercase headers on `oklch(1 0 0 / .02)`, hover rows, tabular-nums.
   - Buttons: primary (blue fill + inset highlight + hover glow) / ghost (hairline).
   - Forms: LatentForge input focus ring (`box-shadow: 0 0 0 3px primary / .25`).
   - Demo tabs + step indicator + forecast tabs: LatentForge `.tabs-list`/`.tab` pill style.
   - Section labels: teal mono `.eyebrow` treatment.
   - Empty states: dashed-border LatentForge `.empty-state`.
   - Research headline: gradient edge-bar panel (`.claim-panel` pattern) with tinted DENY badge.
   - Hero: `bg-grid` masked 56px grid + radial blue glow + gradient-clip `<em>` accent line in the title (LatentForge lab-hero signature).
4. **Fonts:** Inter + JetBrains Mono loaded from Google Fonts in `index.html` (weights 400–700 / 400–500), matching the source site.
5. **Test contract preserved:** `.sidebar__link-label` × 8 in order (Dashboard…Demo), `h1.page__title` per route, `OFFLINE EVALUATION` text, `Quantum/QML: NOT PART OF PROJECT` line (now in header, right-aligned), `.demo-page--presentation .sidebar { display: none }` still hides the header in presentation mode.

## Files changed

| File | Change |
|---|---|
| `src/styles.css` | Complete rewrite (~640 lines): LatentForge token block + component layer mapped to existing class names |
| `src/components/Sidebar.tsx` | Sidebar → sticky top header (brand mark SVG, flat nav, status/authority badges, Quantum footer line) |
| `src/pages/Dashboard.tsx` | One-line hero title edit: `<em>` gradient accent phrase |
| `index.html` | Font preconnect + stylesheet links |

## Verification (exact commands + outcomes)

- `npx vitest run` → **Test Files 5 passed (5), Tests 27 passed (27)** (canvas stderr noise in Forecasts test is pre-existing jsdom limitation, not a failure)
- `npx tsc --noEmit` → exit 0
- `npm run build` → built in 3.73s; `dist/assets/index-*.css` 33.46 kB, JS 437.83 kB
- Live check: Vite dev server (port 5173) hot-reloads the new UI; backend (port 8000) `/health` = `{"status":"ok","api":"UP",...}`

## Governance notes

- Product/frontend only; no policy, registry, protocol-freeze, or Phase 19 artifact touched.
- No test files modified; all 27 tests green unchanged.
- Design system source is the user's own repository (LatentForge), transplanted at the user's explicit request.
