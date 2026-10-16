# Gustavo Style — design system

Reference design system for every HTML surface Gustavo reads: notification emails
and report bodies, the OpenClaw dashboard widgets, and web charts. Other
repositories must not fork this file; they link to it and implement the tokens
below.

- Canonical source: `barbieri-playground/design/DESIGN.md`
- Base inspiration: <https://designmd.app/library/executive-dashboard>
- Applies to: `barbieri-openclaw`, `barbieri-private-openclaw`, `x-summary`,
  `run-and-notify`, `local-openfinance`, and any newer automation that renders
  HTML.

## Principles

1. **Clean, calm, Material-like.** Generous whitespace, one accent color,
   flat surfaces with soft elevation. No gradients, no drop shadows beyond the
   card elevation, no decorative borders.
2. **Readable in both themes.** Every surface must work when the viewer is in
   light mode (Gmail web, Gmail mobile, printer) *and* dark mode (Gmail dark,
   the OpenClaw dashboard). Never rely on a single fixed background.
3. **Semantic color only for meaning.** Success, error, warning, positive and
   negative values get dedicated tokens. Everything else is neutral.
4. **Icons from Material Symbols / Material Icons**, not emoji, in first-party
   UI chrome. Emoji stay allowed inside user-authored content.
5. **Roboto or Open Sans**, nothing else. System fallbacks must cover clients
   that strip web fonts (Gmail does).

## Typography

| Role | Size / weight | Family |
| --- | --- | --- |
| Page title | 24px / 500 | Roboto |
| Section heading | 18px / 500 | Roboto |
| Subsection | 16px / 500 | Roboto |
| Body | 15px / 400 | Roboto |
| Caption / meta | 13px / 400 (muted color) | Roboto |
| Table cell | 14px / 400 | Roboto |
| Metric value | 28px / 500, tabular figures | Roboto |

Font stack (Gmail strips web fonts, so the local fallback is what most readers
see — keep metrics close):

```css
font-family: Roboto, "Open Sans", "Helvetica Neue", Arial, sans-serif;
font-variant-numeric: tabular-nums; /* metric and table columns */
```

Load Roboto where the surface can (`<link>` in HTML documents); never depend on
it being present.

## Color tokens

Brand accent: indigo-blue. Neutrals are cool gray.

### Light theme (emails, light clients)

| Token | Value | Use |
| --- | --- | --- |
| `--surface` | `#ffffff` | Card / page background |
| `--surface-sunken` | `#f6f7f9` | Page background behind cards |
| `--surface-raised` | `#ffffff` | Elevated card |
| `--border` | `#e5e7eb` | Hairline borders, dividers |
| `--border-strong` | `#d8dee8` | Table cell borders |
| `--text` | `#1f2937` | Primary text |
| `--text-muted` | `#64748b` | Captions, meta, labels |
| `--accent` | `#2563eb` | Primary accent, links |
| `--accent-strong` | `#1d4ed8` | Hover / emphasis |
| `--accent-soft` | `#eef2ff` | Accent-tinted background |

### Dark theme (OpenClaw dashboard, dark clients)

| Token | Value | Use |
| --- | --- | --- |
| `--surface` | `#1f2937` | Card background |
| `--surface-sunken` | `#111827` | Page background |
| `--surface-raised` | `#243044` | Elevated card |
| `--border` | `#374151` | Hairline borders, dividers |
| `--border-strong` | `#4b5563` | Table cell borders |
| `--text` | `#f9fafb` | Primary text |
| `--text-muted` | `#9ca3af` | Captions, meta, labels |
| `--accent` | `#60a5fa` | Primary accent, links |
| `--accent-strong` | `#93c5fd` | Hover / emphasis |
| `--accent-soft` | `#1e3a8a` | Accent-tinted background |

### Semantic colors

Chosen to hold contrast on both the light and dark surfaces above.

| Meaning | Light fg / bg | Dark fg / bg | Icons |
| --- | --- | --- | --- |
| Success | `#047857` on `#ecfdf5` | `#34d399` on `#064e3b` | `check_circle` |
| Error | `#b91c1c` on `#fef2f2` | `#fb7185` on `#4c0519` | `error` |
| Warning | `#b45309` on `#fffbeb` | `#fbbf24` on `#451a03` | `warning` |
| Info | `#1d4ed8` on `#eff6ff` | `#60a5fa` on `#1e3a8a` | `info` |
| Positive value | `#16a34a` | `#4ade80` | `trending_up` |
| Negative value | `#dc2626` | `#f87171` | `trending_down` |
| Neutral value | `--text-muted` | `--text-muted` | `trending_flat` |

Rules:

- Never signal meaning with color alone; pair it with an icon or a sign.
- Positive/negative is reserved for **values and deltas**, not decoration.
- Badges use the tinted background + a darker foreground from the same row.

## Charts

Charts must stay legible with color vision deficiency and in both themes.

- **Group related series** (cost categories, investment classes) into a single
  hue family with distinguishable steps, so "everything about costs" reads as
  one visual group.
- **Separate unrelated groups** by hue, not by shade, so groups never blur.
- Minimum **4.5:1** contrast against the chart background for any filled area.
- Never exceed 7 categorical hues; beyond that, aggregate into "Other".

### Categorical palette (hue families)

Each family exposes 5 steps, light → dark. Use a family for one conceptual
group and pick different families for different groups.

| Family | 100 | 300 | 500 | 700 | 900 |
| --- | --- | --- | --- | --- | --- |
| Indigo (accent) | `#e0e7ff` | `#a5b4fc` | `#6366f1` | `#4338ca` | `#312e81` |
| Blue | `#dbeafe` | `#93c5fd` | `#3b82f6` | `#1d4ed8` | `#1e3a8a` |
| Teal | `#ccfbf1` | `#5eead4` | `#14b8a6` | `#0f766e` | `#134e4a` |
| Green | `#dcfce7` | `#86efac` | `#22c55e` | `#15803d` | `#14532d` |
| Amber | `#fef3c7` | `#fcd34d` | `#f59e0b` | `#b45309` | `#78350f` |
| Orange | `#ffedd5` | `#fdba74` | `#f97316` | `#c2410c` | `#7c2d12` |
| Rose | `#ffe4e6` | `#fda4af` | `#f43f5e` | `#be123c` | `#881337` |
| Violet | `#ede9fe` | `#c4b5fd` | `#8b5cf6` | `#6d28d9` | `#4c1d95` |
| Slate (neutral / prior) | `#f1f5f9` | `#cbd5e1` | `#94a3b8` | `#475569` | `#1e293b` |

Assignment rules:

- **Costs / expenses** → Warm families, ranked by size: Amber → Orange → Rose.
- **Investments / holdings** → Cool families: Indigo → Blue → Teal.
- **Income / positive totals** → Green family.
- **Prior period / baseline** → Slate (matches the "prior" series convention).
- Keep a stable mapping: the same category keeps its color across every report
  and every period, so readers learn the mapping once.

### Sequential shading inside a family

For ranked members of one group, step through the family's 500/700/900 for the
largest members and 300/100 for the smallest — this preserves group identity
while keeping neighbors distinguishable.

## Layout and components

- **Page**: max-width 760px for email bodies, centered; 1080px for dashboards.
- **Card**: `--surface-raised`, 1px `--border`, radius 12px, padding 18–24px.
  Elevation is a single subtle shadow at most; dashboards may use none.
- **Metrics row**: label (caption/muted) above value (metric size, tabular).
  Delta shown with icon + signed value in the positive/negative token.
- **Tables**: full width, `--border-strong` cell borders, header row tinted with
  `--accent-soft` or `--surface-sunken`, header weight 500. Numeric columns
  right-aligned with tabular figures.
- **Badges**: pill, 12px/700, tinted background + matching foreground, an icon
  when it conveys state (`check_circle`, `error`, `warning`).
- **Buttons/links**: text links use `--accent`; no underlines except on hover.
- **Spacing scale**: 4, 8, 12, 16, 24, 32 px. Prefer 8/16 for inline rhythm.
- **Radius**: 8px small controls, 12px cards, 999px pills.
- **Divider**: 1px `--border`, vertical margin 22px.

## Theming mechanism

Single source, two themes. Implement tokens as CSS custom properties and flip
them via media query, with an explicit override hook:

```css
:root {
  color-scheme: light dark;
  --surface: #ffffff;
  --text: #1f2937;
  /* …light tokens… */
}
@media (prefers-color-scheme: dark) {
  :root { --surface: #1f2937; --text: #f9fafb; /* …dark tokens… */ }
}
:root[data-theme="light"] { /* force light, for hosts that can set it */ }
:root[data-theme="dark"] { /* force dark */ }
```

Rules:

- **Always set `color-scheme`.** It tells Gmail and browsers which form controls
  and default backgrounds to use and prevents the classic "dark text on a
  transparent background" failure.
- **Never hardcode a text color against an assumed background.** Use tokens; if
  a surface must stay light (e.g. a printed invoice), set an explicit light
  background *and* `color-scheme: light` on that subtree.
- **Email bodies**: Gmail rewrites/uses its own theming. Ship a self-contained
  document with both token sets and `color-scheme: light dark`, and keep the
  body background explicitly set so it does not inherit a transparent one.
- **Dashboard widgets**: the dashboard is dark; honor `prefers-color-scheme`
  and also accept `data-theme` from the host so the board can force a theme.

## Adoption notes per repository

| Repository | Surface | What to change |
| --- | --- | --- |
| `barbieri-openclaw` | daily-calendar / openfinance / slack-summary report HTML | Replace inline styles with these tokens; add `color-scheme`; Roboto stack |
| `barbieri-private-openclaw` | `scripts/generate-daily-tasks-dashboard.py` cards | Already themed dark; move to shared tokens and render HTML reports in iframes |
| `x-summary` | summary markdown → email HTML | Emit token-based HTML; stop leaking pino logs into the captured body |
| `run-and-notify` | `_output-html.hbs` and transport templates | Token-based templates; keep pino logs off stdout |
| `local-openfinance` | `src/intelligence/charts.ts`, report HTML contract | Replace the 6-color `COLORS` array with the family palette; group cost vs investment hues |

## Definition of done for an adopting surface

1. Renders correctly in Gmail light **and** Gmail dark (test both).
2. Renders correctly as an OpenClaw dashboard widget (dark) and via the sandbox.
3. No hardcoded text color without a matching background.
4. `color-scheme` is set.
5. Chart colors follow the family rules and are stable across periods.
6. Icons are Material, not emoji, in UI chrome.
7. Screenshot evidence attached for both themes.
