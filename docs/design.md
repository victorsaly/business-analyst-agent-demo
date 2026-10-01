---
name: Business Performance Analyst Agent
description: A six-minute demo pressed onto a hand-lettered cassette J-card, ballpoint ink on ruled inlay stock.
colors:
  ballpoint-ink: "#1E3A8A"
  ink-pressed: "#172F73"
  faded-ink: "#3F5A9E"
  printed-red: "#C62828"
  red-ink: "#B71C1C"
  inlay-paper: "#FCFBF7"
  blank-white: "#FFFFFF"
  blue-wash: "#EEF2FB"
  ruled-line: "#DBE2F1"
  mid-rule: "#A9B8DC"
  pencil-grey: "#687083"
  chart-ink-blue: "#2B4BB0"
  chart-pencil-ochre: "#B7791F"
  chart-faded-blue: "#6B86C5"
  chart-other-grey: "#8E98AE"
  chart-gridline: "#D3DBEE"
typography:
  display:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "5.4rem"
    fontWeight: 400
    lineHeight: 0.98
    letterSpacing: "0.01em"
  headline-page:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "3.6rem"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "0.01em"
  headline:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "3rem"
    fontWeight: 400
    lineHeight: 1.08
    letterSpacing: "0.01em"
  title:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "1.8rem"
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: "0.01em"
  lede:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "1.75rem"
    fontWeight: 400
    lineHeight: 1.35
  track:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "1.32rem"
    fontWeight: 400
    lineHeight: 1.2
  label:
    fontFamily: "Patrick Hand SC, Patrick Hand, Marker Felt, cursive"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1
  answer:
    fontFamily: "Patrick Hand, Marker Felt, cursive"
    fontSize: "1.5rem"
    fontWeight: 400
    lineHeight: 1.45
  body:
    fontFamily: "Patrick Hand, Marker Felt, cursive"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.45
  note:
    fontFamily: "Patrick Hand, Marker Felt, cursive"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.45
  typed:
    fontFamily: "Courier Prime, Courier New, monospace"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  typed-strong:
    fontFamily: "Courier Prime, Courier New, monospace"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
    fontFeature: "tnum"
rounded:
  none: "0px"
spacing:
  hairline-gap: "4px"
  inset-sm: "0.6rem"
  inset-md: "1rem"
  panel-x: "1.4rem"
  ruled-line: "2rem"
  gutter: "2.25rem"
  column-gap: "2rem"
  pair-gap: "3rem"
  masthead: "4.5rem"
  spine: "6rem"
components:
  button-primary:
    backgroundColor: "{colors.ballpoint-ink}"
    textColor: "{colors.inlay-paper}"
    typography: "{typography.track}"
    rounded: "{rounded.none}"
    padding: "0.65rem 1.3rem"
  button-primary-hover:
    backgroundColor: "{colors.ink-pressed}"
    textColor: "{colors.inlay-paper}"
  button-secondary:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.track}"
    rounded: "{rounded.none}"
    padding: "0.65rem 1.3rem"
  button-secondary-hover:
    backgroundColor: "{colors.blue-wash}"
    textColor: "{colors.ballpoint-ink}"
  button-warn:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.red-ink}"
    rounded: "{rounded.none}"
    padding: "0.65rem 1.3rem"
  button-disabled:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.pencil-grey}"
  mode-switch:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.label}"
    padding: "0.3rem 0.8rem"
  mode-switch-active:
    backgroundColor: "{colors.ballpoint-ink}"
    textColor: "{colors.inlay-paper}"
  tag:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.3rem 0.55rem 0.25rem"
  tag-live:
    backgroundColor: "{colors.ballpoint-ink}"
    textColor: "{colors.inlay-paper}"
  tag-dry-run:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.red-ink}"
  input:
    backgroundColor: "{colors.blank-white}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0.5rem 0.65rem"
  track-row:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.track}"
    padding: "0.3rem 0.4rem"
  track-row-current:
    backgroundColor: "{colors.blue-wash}"
    textColor: "{colors.ballpoint-ink}"
  panel:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    rounded: "{rounded.none}"
    padding: "1rem 1.4rem"
  now-playing:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.ballpoint-ink}"
    rounded: "{rounded.none}"
    padding: "1.4rem 1.8rem 1.8rem"
  typed-block:
    backgroundColor: "{colors.blank-white}"
    textColor: "{colors.ballpoint-ink}"
    typography: "{typography.typed}"
    rounded: "{rounded.none}"
    padding: "0.6rem 0.8rem"
  margin-note:
    backgroundColor: "{colors.inlay-paper}"
    textColor: "{colors.red-ink}"
    rounded: "{rounded.none}"
    padding: "0.55rem 0.8rem"
---

# Design System: Business Performance Analyst Agent

## Overview

**Creative North Star: "The Six-Minute Mixtape"**

The demo looks like an unfolded cassette J-card (the paper insert in a cassette case), written up by hand. A vertical spine runs down the left edge with the title, a red triple stripe and an A/B box. The main panel is ruled inlay stock. Every screen is a part of the card: the tracklist is the demo plan, each prepared case is a track with a running time, side A holds the brief's questions and side B the guardrails. The tape counter and a thin red position bar move while a run plays. Text is ballpoint ink throughout. Red is the printed second colour: the stripe, the running bar, corrections and refusals. Charts are drawn in the same ink on the same paper.

The system is flat, square and inked. Depth comes from rules and boxes; there are no shadows. Type carries the brand: hand-lettered block caps for anything you would letter onto a card, handwritten prose for answers, and typewriter for anything the machine produced (SQL, tool names, counters, figures). It deliberately avoids the usual dark AI dashboard with KPI tiles and chat bubbles.

It is built to be read from the back of a lit room on a washed-out projector. The root font size is large (18px, rising to 21px at 1800px and wider), contrast is ink on near-white, and no state relies on colour alone: the active screen gets an underline, the current track gets a wash and a red number, and a dry run gets a red box plus written words.

Main characteristics:

- Two-ink print: ballpoint blue for everything, one printed red for signals; ochre appears only in charts.
- Ruled paper ground: a faint blue line every 2rem across the whole page, so content sits on lines like handwriting.
- Three voices of type: lettered caps (Patrick Hand SC), handwriting (Patrick Hand), typewriter (Courier Prime).
- Square hairline boxes (1.5px ink) and heavier 2–2.5px rules under headings; no radius, no shadow.
- A fixed spine plus a sticky masthead with the screen nav, the mode switch and the tape counter.

## Colors

A two-ink print on cream-white stock: one deep ballpoint blue carries all text and structure, one printed red carries signals, and a set of pale blues is used for rules and washes.

In `app/web/app.css` the colours are CSS custom properties on `:root`. The CSS names are shorter than the token names used on this page (`--ink` is Ballpoint Ink, `--ink-2` is Faded Ink, `--rule-mid` is Mid Rule, `--pencil` is Pencil Grey):

```css
:root {
  --paper: #fcfbf7;     /* inlay-paper */
  --wash: #eef2fb;      /* blue-wash */
  --ink: #1e3a8a;       /* ballpoint-ink */
  --ink-2: #3f5a9e;     /* faded-ink */
  --rule: #dbe2f1;      /* ruled-line */
  --rule-mid: #a9b8dc;  /* mid-rule */
  --red: #c62828;       /* printed-red */
  --red-ink: #b71c1c;   /* red-ink */
  --pencil: #687083;    /* pencil-grey */
  ...
}
```

### Primary
- **Ballpoint Ink** (`ballpoint-ink`): all text, every box outline, heading rules, the spine border, filled primary buttons, the active mode and the active side tab. Inverted (paper on ink) for selection and solid tags.
- **Pressed Ink** (`ink-pressed`): hover state of the filled primary button only.
- **Faded Ink** (`faded-ink`): secondary text such as track numbers, notes, figure captions, query labels, the "how I got this" footer and the side-budget line. It is still ink, only older and less pressed.

### Secondary
- **Printed Red** (`printed-red`): the brand stripe on the spine, the run-position bar, the active-nav underline, the margin line beside the tracklist, list bullets, the focus ring, the text caret and the "writing…" cursor block, plus outlines for refusals, slips and margin notes.
- **Red Ink** (`red-ink`): red text, which is darker so it holds contrast on paper: the catalogue time on the spine, the current track number, error and refused steps, the dry-run note, footnote numbers `[1]`, failed scorecard marks and a counter that has gone over 6:00.

### Neutral
- **Inlay Paper** (`inlay-paper`): the page, every panel and the chart background. It is never pure white.
- **Blank White** (`blank-white`): only where something gets written or typed into the card: text inputs, the textarea, and the typed SQL blocks.
- **Blue Wash** (`blue-wash`): hover and the current track row; the secondary button's hover.
- **Ruled Line** (`ruled-line`): the background rules every 2rem on the page and on the downloadable briefing.
- **Mid Rule** (`mid-rule`): row dividers in lists, tables, tracklists and step logs; borders on typed blocks and chart images; scrollbar thumb; the hover underline in the nav.
- **Pencil Grey** (`pencil-grey`): disabled controls, placeholders and the track sub-line (for example "No recording yet"). It means "not available", not hierarchy.

### Chart palette
Charts are drawn by matplotlib in `app/analyst/tools.py` on the same paper, with the same fonts. The colours are set at the top of the chart code:

```python
_INK, _INK_SOFT, _PAPER, _RULE, _OTHER = "#1E3A8A", "#3F5A9E", "#FCFBF7", "#D3DBEE", "#8E98AE"
_SERIES = ["#2B4BB0", "#B7791F", "#6B86C5"]   # red is kept for negative values only
_NEG = "#C62828"
```

- **Chart Ink Blue** (`chart-ink-blue`): series 1, and every bar in a single-series chart.
- **Chart Pencil Ochre** (`chart-pencil-ochre`): series 2. The only place ochre appears in the system.
- **Chart Faded Blue** (`chart-faded-blue`): series 3.
- **Chart Other Grey** (`chart-other-grey`): the "Other" bucket in breakdowns.
- **Chart Gridline** (`chart-gridline`): value-axis gridlines. The baseline spine is Ballpoint Ink at 1.4pt, and the other three spines are removed.

This categorical set was checked for colour-blind separation and contrast against Inlay Paper.

### Named Rules
**The Red Is Not Data Rule.** Printed Red never encodes a data series. In charts it marks negative values only (negative bars turn red). In the UI it means signal: brand stripe, running, correction, refusal, current position. If a third series is needed, use Chart Faded Blue, never red.

**The Two-Ink Rule.** Interface chrome uses only the blues and the red. Ochre lives in charts and nowhere else.

**The Paper Is Not White Rule.** Surfaces are Inlay Paper. Blank White appears only inside fields and typed blocks, the places where something is written or typed onto the card.

## Typography

**Display Font:** Patrick Hand SC (with Patrick Hand, Marker Felt, cursive)
**Body Font:** Patrick Hand (with Marker Felt, cursive)
**Label/Mono Font:** Courier Prime (with Courier New, monospace)

All three are self-hosted OFL (open-licence) fonts in `app/web/fonts`, loaded with `font-display: block` so the card never flashes a system font while they load. The downloadable briefing embeds them as base64, so it looks the same when emailed or printed.

```css
@font-face { font-family: "Patrick Hand SC"; src: url("fonts/PatrickHandSC-Regular.ttf") format("truetype"); font-display: block; }
@font-face { font-family: "Patrick Hand"; src: url("fonts/PatrickHand-Regular.ttf") format("truetype"); font-display: block; }
@font-face { font-family: "Courier Prime"; src: url("fonts/CourierPrime-Regular.ttf") format("truetype"); font-weight: 400; font-display: block; }
```

**Character:** Block caps lettered with a marker for anything a person would write on the card, a looser hand for the answer prose, and a typewriter label for anything the machine produced. Hand-lettered headings (h1–h3) carry a thin `-webkit-text-stroke` of 0.035em in the current colour (`paint-order: stroke fill`) so they look as if drawn with a marker. Track titles, nav links, buttons, scorecard questions, the side total and the spine title carry a lighter 0.02em stroke:

```css
h1, h2, h3 { font-family: var(--hand-sc); font-weight: 400; -webkit-text-stroke: 0.035em currentColor; paint-order: stroke fill; }
.track .t, .list li .t, .score-row .q, .masthead nav a, .btn, .rule-head .total, .spine .title { -webkit-text-stroke: 0.02em currentColor; }
```

### Hierarchy
- **Display** (`display`): the Cover title only, set over three lines with a 4px ink underline bar.
- **Headline Page** (`headline-page`): the titles of the What changed, Tools, Briefing and Scorecard screens.
- **Headline** (`headline`): the question on the now-playing inlay, followed by a 3px ink rule. The empty state ("Pick a track.") is a little larger, at 3.4rem.
- **Title** (`title`): section heads such as "Answer", "How I got this" and "Side A", always on a 2.5px ink rule.
- **Lede** (`lede`): the Cover tagline, in lettered caps.
- **Track** (`track`): track names, list items, scorecard questions and buttons (1.3–1.35rem). Nav links are 1.3rem.
- **Label** (`label`): tags, field labels, mode-switch buttons, side tabs and table headers (1.05–1.2rem).
- **Answer** (`answer`): the answer prose, capped at 58rem wide.
- **Body** (`body`): the default running text on the page.
- **Note** (`note`): secondary text in Faded Ink: notes, captions, track descriptions (1.05–1.2rem).
- **Typed** (`typed`, `typed-strong`): SQL, tool names in the step log (bold), the tape counter (bold, 1.35rem), the catalogue mark, the footer metrics, the numeric table cells (right-aligned, tabular) and the margin formula.

The root is 18px, 21px at 1800px and wider (for projectors), and 16px at 1100px and below. All sizes are in rem, so they scale from that root:

```css
html { font-size: 18px; }
@media (min-width: 1800px) { html { font-size: 21px; } }
@media (max-width: 1100px) { html { font-size: 16px; } }
```

### Named Rules
**The Three Voices Rule.** Lettered caps for labels and titles, handwriting for prose, typewriter for anything the machine produced. Never set SQL or numbers from a query in a hand face, and never set prose in the typewriter.

**The Marker Weight Rule.** The hand faces only come in weight 400, so weight comes from the text stroke, never from `font-weight: bold` (which would synthesise a faux bold). Use 0.035em on headings and 0.02em on lettered labels.

## Layout

The page is a two-column grid: a 6rem spine and the card. The spine is sticky and full height: the red triple stripe (three 5px bars, 4px apart), the catalogue mark ("6:00 / CP-02 / 1–2 Oct 26": the demo running time, Capstone Project 2 of 5, and the workshop dates), the vertical title rotated to read bottom-up, and the A/B box with the date span. The masthead is sticky, 4.5rem high, ruled underneath with 2px ink, and holds the screen nav on the left with the mode switch and tape counter on the right. Directly under it is a 4px red position bar that scales from the left as a run plays.

Main content has 2.25rem side gutters and 2rem top padding. The paper is ruled every 2rem (`ruled-line`), and list rows, requirement rows and track rows are at least one ruled line high so they sit on the lines. The rules are a hard-stop gradient on the page background:

```css
body {
  background-color: var(--paper);
  background-image: linear-gradient(to bottom, transparent calc(var(--line) - 1px), var(--rule) calc(var(--line) - 1px), var(--rule) var(--line), transparent var(--line));
  background-size: 100% var(--line);   /* --line: 2rem */
}
```

- **Tracks** is a deck: the tapelist on the left (minimum 27rem, about a third, sticky under the masthead), the now-playing inlay on the right; 2rem gap.
- **Cover** is a 1.25 : 1 split: the title block on the left, a ruled panel ("How it plays", "House rules") on the right; 3rem gap, vertically centred.
- **What changed** uses a 1 : 1 before/after pair with a 3rem gap, then the requirements list and folding detail sections.
- **Briefing / Scorecard** sit on one ruled sheet, max 66rem wide.
- Reading widths are capped: answer 58rem, charts and notes 62rem, notes and slips 52rem.

On smaller screens: at 1100px and below the root drops to 16px, and every split collapses to one column; the tapelist stops being sticky. At 700px and below the spine becomes a horizontal top strip (no A/B box, a wrapping title), the masthead wraps and stops being sticky, gutters shrink to 1rem, and requirement rows drop their category and points columns.

## Elevation & Depth

The system is flat. There is no `box-shadow` anywhere in the build. Hierarchy comes from line weight and from the paper: 1px Mid Rule for row dividers, 1.5px ink for boxes, tags and controls, 2px ink for structural edges (spine, masthead, buttons), 2.5px ink under section heads, and 3–4px ink bars under the big titles. The only "lift" is the Blue Wash on hover and on the current row, and the inverted ink fill for active states.

### Named Rules
**The Ink, Not Light Rule.** To separate something, give it a heavier rule or a box. Do not use a shadow, a blur or a soft gradient. Hard-stop gradients are fine only as a way to draw ruled lines (the paper rules, the tracklist margin line).

## Shapes

Every corner is square (`rounded.none`). Inputs explicitly reset to a 0 radius. Boxes are hairline ink outlines on paper, like the printed panels of a J-card. Recurring marks:
- the red triple stripe on the spine;
- a 1px red vertical margin line running through the tracklist behind the track numbers, like the margin rule on lined paper;
- a heavy ink rule under every heading;
- bracketed red footnote numbers `[1]`, `[2]` before each liner-note query;
- line icons (play, flip, download, tick, cross, plus, pen) drawn at 2px with round caps and joins, 1.1em, in the current colour.

The one rounded shape is the WebKit scrollbar thumb (6px), which is browser chrome rather than part of the card.

## Components

### Buttons
Buttons use lettered caps in square ink boxes, like boxes ruled onto the card.
- **Shape:** square (`rounded.none`), 2px ink border, icon and label 0.55rem apart.
- **Primary:** ink fill with paper text; for the main action on a screen ("Play side A", "Ask").
- **Secondary:** paper fill with an ink outline and ink text.
- **Warn:** red outline with Red Ink text, for destructive or reset actions.
- **Hover / Active:** secondary hovers to Blue Wash, primary darkens to Pressed Ink (160ms); press nudges down 1px (120ms).
- **Disabled:** Pencil Grey text and a Mid Rule border on paper; `not-allowed` cursor.
- **Link-style action:** an underlined handwriting link ("New conversation") for low-stakes actions.

### Mode switch
A segmented box of three lettered buttons (Live AI, Replay, Dry run) joined by 1.5px ink dividers. The active mode is filled with ink. The mode is also restated on the now-playing inlay as a tag: **Live** is a solid ink tag, **Replay** an outline tag, **Dry run** a red-outlined tag plus a written red note. The mode is never shown by colour alone.

### Tags
- **Style:** lettered caps in a 1.5px ink box, square, compact padding.
- **Variants:** outline (default), solid (ink fill, paper text), red (red border, Red Ink text).

### Cards / Containers (panels)
- **Corner Style:** square.
- **Background:** Inlay Paper, so the ruled lines stop at the box edge and the box reads as a pasted panel.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1.5px ink.
- **Internal Padding:** 1rem 1.4rem for panels and before/after pairs; 1.4rem 1.8rem for the now-playing inlay and the sheet.

### Inputs / Fields
- **Style:** 1.5px ink border, Blank White fill, square, handwriting at 1.2–1.25rem. The textarea switches to the typewriter. Placeholders are Pencil Grey.
- **Labels:** lettered caps above the field.
- **Focus:** the global focus ring, a 2px Printed Red outline offset 3px. The caret is red too:

```css
:focus-visible { outline: 2px solid var(--red); outline-offset: 3px; }
body { caret-color: var(--red); }
```

### Navigation
Lettered caps links in the masthead, 1.6rem apart, with no default underline. Hover shows a 2.5px Mid Rule underline. The current page gets a 2.5px Printed Red underline (`aria-current="page"`). At 700px and below the links wrap.

### Tracklist (signature)
The demo plan as a cassette tracklist inside a ruled box. Side A / Side B tabs (a segmented box like the mode switch) flip the face with a y-axis turn (rotate to 90°, 220ms, opacity to 0.2). Each track is a full-width button laid out as number · title · running time, with a Pencil Grey sub-line when a recording is missing. Hover and current rows get Blue Wash, and the current number turns Red Ink. The side's summed time sits in the heading against 6:00, and the "both sides" budget sits underneath. A hidden bonus track sits below a typed gap marker and is labelled as a planted rehearsal anomaly. Pressing a track plays it: this is the screen's primary action.

### Step log (signature)
A numbered list where each tool step is inked in as it arrives, with a left-to-right `clip-path` reveal of 340ms:

```css
@keyframes ink { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
.steps li { border-bottom: 1px solid var(--rule-mid); animation: ink 340ms var(--ease) both; }
```

Each row shows a lettered number, the bold typed tool name and a handwriting summary. Refused or errored steps turn Red Ink. Queries fold open in a typed SQL block. While the agent works, a "writing…" line ends in a blinking red caret block (1s, stepped).

### Liner notes
The "How I got this" section is an ordered list of the exact queries from the tool log. Each has a red bracketed number, a typed label and a typed SQL block (Blank White, 1px Mid Rule border). A typed footer gives tool calls, tokens, seconds and model.

### Tape counter and position bar
A bold typed counter (tabular numbers) in the masthead counts up while a run plays, with a smaller Faded Ink suffix, and turns Red Ink when over. A 4px red bar under the masthead scales across in step (250ms linear).

### Margin note and slip
Presenter-only "Point out:" notes, and refusal or limit slips: handwriting in Red Ink inside a 1.5px red box on paper, with the lead word in lettered caps.

### Ruled table
Lettered header cells on a 2.5px ink rule, rows on 1px Mid Rule, numeric cells in the typewriter, right-aligned with tabular numbers. Used for KPIs, tool results and the briefing.

### Chart figure
Charts are matplotlib PNGs on Inlay Paper, with a lettered caps title on the left (19pt), handwriting tick labels (15pt), typewriter value labels (14pt), gridlines only on the value axis, and a single ink baseline. They are shown with a 1px Mid Rule border and a Faded Ink caption ("chart_1: …").

### Downloadable briefing page
A self-contained miniature of the card at fixed pixel sizes: a 64px spine with a 3-bar red stripe and vertical title, 17px handwriting body, rules every 28px, a 32px lettered h1 on a 3px rule, tables and liner notes as in the app, and embedded fonts. The outer border is dropped when printing.

## Do's and Don'ts

### Do:
- Do set every surface on Inlay Paper with the 2rem ruled lines, and keep row heights at a minimum of one ruled line.
- Do separate content with ink rules and 1.5px boxes: 1px Mid Rule between rows, 2.5px ink under headings.
- Do use the three voices strictly: lettered caps for titles and labels, handwriting for prose, Courier Prime for SQL, tool names, counters and figures.
- Do give hand-lettered headings the 0.035em text stroke (0.02em on lettered labels) instead of a bold weight.
- Do reserve Printed Red for the stripe, the running bar, the current position, corrections, refusals and focus.
- Do draw chart series in Chart Ink Blue, Chart Pencil Ochre and Chart Faded Blue, in that order, with "Other" in Chart Other Grey and negatives in red.
- Do state every mode in words as well as style (solid, outline or red tag, plus the dry-run note).
- Do keep motion short and purposeful (160ms hovers, 220ms side flip, 340ms ink reveal), and turn all of it off for people who ask their system for reduced motion:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
```


### Don't:
- Don't use rounded corners, drop shadows, blurs or soft colour gradients on any card element (hard-stop gradients that draw ruled lines are the paper itself, and are fine).
- Don't use red as a data series, or ochre in interface chrome.
- Don't use pure white as a surface; it is only for fields and typed blocks.
- Don't set prose or headings in a system sans or serif. If a hand face fails to load, the fallback is Marker Felt or cursive, never Arial or Inter.
- Don't fake bold on Patrick Hand or Patrick Hand SC with `font-weight: 700`.
- Don't turn the screens into a dark AI dashboard with KPI tiles and chat bubbles; answers are inked onto the card, not spoken in bubbles.
