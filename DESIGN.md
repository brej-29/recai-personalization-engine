---
name: Kindred
description: A seven-segment instrument for cross-media taste, in LED (dark) and LCD (light) skins.
colors:
  ground: "#0c0b0a"
  panel: "#131110"
  raise: "#1a1715"
  line: "#2b2622"
  ghost: "#231e1a"
  ghost-lit: "#342d27"
  text: "#ece5d8"
  dim: "#a3998b"
  faint: "#8f8577"
  lit: "#ff4a3d"
  focus: "#ffd24a"
  anime-red: "#ff5a4a"
  film-amber: "#ff9a2e"
  manga-yellow: "#f4dc3c"
  manhwa-green: "#6fe05c"
  manhua-cyan: "#34e3b8"
  novel-blue: "#3cc8ff"
  movie-lilac: "#b8a0ff"
  series-pink: "#ff72b5"
typography:
  display:
    fontFamily: "Hanken Grotesk Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(2rem, 3.4vw, 3rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Hanken Grotesk Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Hanken Grotesk Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Hanken Grotesk Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "'tnum' 1"
  label:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 500
    lineHeight: 1
    letterSpacing: "0.14em"
rounded:
  sharp: "2px"
  well: "3px"
  dot: "50%"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "28px"
  xl: "40px"
components:
  skin-toggle-active:
    backgroundColor: "{colors.lit}"
    textColor: "{colors.ground}"
    rounded: "{rounded.sharp}"
    padding: "7px 10px"
  field-input:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.sharp}"
    padding: "14px"
  lamp:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.dim}"
    rounded: "{rounded.sharp}"
    padding: "9px 10px"
  lamp-pressed:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
  seed-slot:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.sharp}"
    height: "40px"
  result-row:
    textColor: "{colors.text}"
    height: "78px"
  scoreboard-well:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.text}"
    rounded: "{rounded.well}"
    padding: "6px 20px 10px"
---

# Design System: Kindred

## Overview

**Creative North Star: "The Seven-Segment Console"**

Kindred reads like an appliance, not a feed. Taste is shown as lit segments on a matte, warm near-black ground: ranks, match values and the wordmark are all drawn by one eight-cell segment mask, and every unlit segment is drawn too, as a dim ghost cell. Labels are appliance silkscreen (condensed, uppercase, tracked); running text is a quiet grotesk. Cover art is secondary to the readout.

Two skins share every structure and differ only in tokens. LED is the default: warm black with lit hues. LCD is a pale grey-green calculator ground with dark segments and no bloom. Each of the eight media owns one hue, so a medium is recognisable from a lamp, a chip or a segment colour alone.

Density is panel-like: hairline rules, 2px corners, fixed row heights ("place never moves, only segments change").

**Key Characteristics:**
- One segment mask for numerals, the wordmark and labels-as-glyphs; ghost cells always visible.
- Eight medium hues, redefined (darker) in the LCD skin so contrast holds.
- Hairline 1px rules instead of cards or shadows; sharp 2px corners.
- A short bloom on lit elements in LED only; none in LCD.
- Stepped, quantised motion (blink, stepped meter fill), never smooth sweeps.

## Colors

A warm black console with one alarm-red lit colour and eight indicator hues, each tied to a medium.

### Primary
- **Lit Alarm Red** (`lit`): the default lit-segment colour, the active skin switch, the caret, the toggle knob when on, the hot edges in the pipeline diagram and the top scoreboard value. In LCD it becomes the ink colour (#1b2514).
- **Focus Amber** (`focus`): the keyboard focus ring only (2px). In LCD it is a dark oxblood (#7a1f12).

### Secondary (medium hues, indexed 0 to 7)
- **Anime Red** (`anime-red`), **Film Amber** (`film-amber`), **Manga Yellow** (`manga-yellow`), **Manhwa Green** (`manhwa-green`), **Manhua Cyan** (`manhua-cyan`), **Novel Blue** (`novel-blue`), **Movie Lilac** (`movie-lilac`), **Series Pink** (`series-pink`): in that order, for anime, anime films, manga, manhwa, manhua, novels, movies, series. Used for the match readout, chip dot and code, lamp indicator, atlas dots and cover-tile fallbacks. Anime Red also marks "zero" and a failed verdict; Manhwa Green marks a passed verdict.

### Neutral
- **Warm Ground / Panel / Raise** (`ground`, `panel`, `raise`): page, wells and inputs, then popovers.
- **Rule** (`line`): every divider and border.
- **Ghost / Ghost Lit** (`ghost`, `ghost-lit`): unlit segments, meter tracks, off lamps; the lit variant is for loading digits and hover.
- **Text / Dim / Faint** (`text`, `dim`, `faint`): primary, secondary and tertiary copy.

LCD values (ground #c4cca9, ink #1b2514, hues #8f1d12 through #8a1c57) live in the sidecar and `:root[data-skin='lcd']`.

### Named Rules
**The Hue-Is-Medium Rule.** A medium hue marks that medium and nothing else. Never reuse one as a generic accent.
**The Ghost Rule.** Every segment display draws its unlit cells. A lit value without its ghost is not a display.

## Typography

**Display and Body Font:** Hanken Grotesk Variable (with Segoe UI, system-ui)
**Label Font:** Barlow Condensed 500/600/700 (with Arial Narrow)

**Character:** A quiet, tight grotesk for reading beside condensed silkscreen labels. The numerals that matter are not type at all: they are segment glyphs.

### Hierarchy
- **Display** (700, clamp(2rem, 3.4vw, 3rem), 1.02, -0.03em): the rail headline; one lit word in `lit`.
- **Headline** (700, clamp(1.8rem, 3.2vw, 2.8rem), 1.05, -0.03em, max 22ch): evidence section titles.
- **Title** (700, 1.25rem, 1.2): sub-sections.
- **Body** (400, 1rem, 1.55, tabular figures on): ledes cap at 62ch, notes at 60ch, long rationale at 70ch.
- **Label** (500 to 600, 0.72 to 0.85rem, 0.14em tracking, uppercase): field labels, nav, lamps, verdicts, table heads, chip codes.

### Named Rules
**The Silkscreen Rule.** Condensed uppercase tracked type is for labels on the instrument only; sentences stay in the grotesk.

## Layout

A three-column console: rail (300 to 380px) / results board (fluid) / atlas (about 36%, sticky, full viewport height). Below 1100px the atlas drops to a full-width 62svh band; below 760px everything stacks and secondary nav links hide. The evidence story below is centred at 1240px max with section padding of clamp(56px, 10vw, 128px). Rows are fixed height (78px, 74px mobile) in a four-column grid: rank, cover, meta, match. Gaps follow 6 / 10 / 14 / 18 / 28 / 40px. Page gutters use clamp(16px, 3vw, 40px).

## Elevation & Depth

Flat and tonal. Depth is ground, panel, raise, with 1px rules. Two shadows exist: an inset recess (`inset 0 2px 10px #0006`) on the scoreboard and silo wells, as if the panel were sunk into the chassis, and one drop shadow (`0 12px 28px -8px #000a`) under the search suggestions popover. The only glow is the bloom on lit segments and lamps: `drop-shadow(0 0 calc(var(--bloom) * 5px))`, `--bloom` 0.55 in LED and 0 in LCD.

### Named Rules
**The Short Bloom Rule.** Glow is at most 9px, only on something lit, and scales with `--bloom`.

## Shapes

Hard-edged hardware: 2px corners on controls, inputs, covers and slots; 3px on sunk wells; circles only for lamps and status dots. Segments are skewed -6deg bars with chamfered ends. Dashed borders mean an empty slot; solid means filled. Meters are 6px lit blocks on 2px gaps.

## Components

### Segment display
Eight-cell mask (seven-segment for digits, 14-segment letters and diagonals for the wordmark). Sized by `--sh`: 18px (slots), 22px (scoreboard), 26px (rank, match, wordmark), up to 120px (ledger). `ghosted` states use `ghost-lit`; the wordmark hides unlit cells.

### Skin switch
A two-button group with a 1px rule; the pressed side fills `lit` with `ground` text.

### Search field
Panel fill, 1px rule, 2px corners; focus swaps the border to `lit` (inside the ring). Suggestions float in a raised popover; the selected row takes `ghost-lit`.

### Lamps and toggle
Medium filters are lamps: panel button, 9px dot that lights in the medium hue with bloom when pressed, border takes the hue. The "All" lamp spans the grid. The blend toggle is a 34x18 slot with a sliding knob.

### Seed slots
Five 40px rows with a segment index; dashed when empty, solid on panel when filled.

### Result row
78px grid: segment rank, 54x64 cover (image over a hatched, hue-tinted title tile), title with chip code and a one-line "why", and the match value in the medium hue.

### Scoreboard
Panel well with inset recess. Each row: name, segmented meter (stepped fill, confidence interval whiskers, tick scale), value in segments (top row in `lit`), interval text. Verdicts are a 22x8 lamp bar: green for yes, red for no, ghost otherwise.

### Atlas
Dot-matrix canvas of all titles in medium hues, seed ignited with arcs to kin; legend of eight code and label pairs beneath.

### Motion
Ease `cubic-bezier(0.16, 1, 0.3, 1)` for toggles; the demo status dot blinks in two steps; meters fill in 36 steps over 1.1s; evidence blocks rise 14px on scroll entry through `animation-timeline: view()` (progressive enhancement). All of it is switched off under `prefers-reduced-motion`.

## Do's and Don'ts

### Do:
- **Do** route every colour through the skin tokens so LED and LCD both work.
- **Do** draw ghost cells for every segment display, and keep place fixed while values change.
- **Do** keep medium identity in text (code or label) as well as hue.
- **Do** use `focus` 2px outlines with 2px offset for all keyboard focus.

### Don't:
- **Don't** add a bloom in the LCD skin or wider than 9px in LED.
- **Don't** build cover-grid or card-feed layouts; cover art stays at 54px beside the readout.
- **Don't** use a medium hue for anything but its medium (and the red/green verdicts).
- **Don't** use smooth sweeping motion for data; quantise it into steps.
