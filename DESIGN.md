---
name: CAHMA Control
description: A planar optical metrology bench for policy-governed edge-vision allocation.
colors:
  ground: "#0d1114"
  panel: "#12181c"
  panel-2: "#182126"
  steel: "#273238"
  line: "#354248"
  muted: "#92a0a6"
  faint: "#6f7c82"
  ink: "#dce2e3"
  signal: "#668c9c"
  signal-bright: "#88acba"
  amber: "#ba8646"
  red: "#ad5c55"
  good: "#7f9f85"
typography:
  display:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "clamp(23px, 2.2vw, 34px)"
    fontWeight: 600
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Bahnschrift, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    letterSpacing: "0.02em"
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "normal"
  label:
    fontFamily: "Cascadia Mono, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.08em"
rounded:
  square: "0px"
spacing:
  micro: "4px"
  xs: "7px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "26px"
components:
  instrument-panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "{spacing.md}"
  camera-index-item:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "11px"
    height: "74px"
  measured-feed:
    backgroundColor: "#080b0d"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
  control-button:
    backgroundColor: "#17242a"
    textColor: "{colors.signal-bright}"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "34px"
  control-button-hover:
    backgroundColor: "#203139"
    textColor: "{colors.signal-bright}"
  control-button-release:
    backgroundColor: "#282018"
    textColor: "#d2a66f"
    rounded: "{rounded.square}"
    padding: "0 12px"
    height: "34px"
  candidate-row:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.square}"
    padding: "0 10px"
    height: "47px"
  candidate-row-selected:
    backgroundColor: "#162229"
    textColor: "{colors.ink}"
---

# Design System: CAHMA Control

## Overview

**Creative North Star: "Optical Metrology Bench"**

CAHMA Control is built as a measured industrial instrument, not a generic dashboard. Anodized graphite planes, steel rules, engraved labels, desaturated camera fields, tabular readings, and sparse signal colors make policy-governed allocation visible as a physical-feeling operating bench. The surface is dense but ordered: the live mechanism is dominant, while every surrounding panel explains what the runtime admitted, selected, inferred, or retained.

The composition tells one continuous story: choose a camera in the index, inspect its measured feed, read the fixed dispatch and capacity rail, compare the camera array, scan the ranked candidate field, then follow the retained decision sequence into policy and evidence. Runtime absence is never cosmetically repaired. Unconfirmed fixtures, empty readings, stale events, rejected capacity, and disabled controls remain visibly distinct from healthy operation.

**Key Characteristics:**

- Planar graphite surfaces separated by steel rules, never floating cards.
- Square instrument geometry with right-angle reticles, meters, cells, and state marks.
- Measured video as the visual center, with coordinates, detections, tally, and numeric strips attached to the frame.
- A narrow camera index and fixed instrumentation rail that keep selection, dispatch, capacity, and policy in view.
- Cyan-steel for focus and inference, with muted green, amber, and red reserved for semantic state.
- Compact system typography and tabular data that stay legible in a projected laptop demo.

## Colors

The palette is a low-chroma graphite-and-steel field with a single calibration-cyan voice and restrained operational status colors.

### Primary

- **Calibration Steel** (`colors.signal`): borders, route lines, selected detection labels, and controlled emphasis.
- **Calibration Cyan** (`colors.signal-bright`): active inference, focus, current selection, instrument labels, and the CAHMA wordmark accent.

### Secondary

- **Admission Amber** (`colors.amber`): connecting, stale, fixture, override-release, and other cautionary states.
- **Fault Red** (`colors.red`): disconnected, degraded, blocked, rejected, and error states.
- **Admitted Green** (`colors.good`): live, eligible, warmed, accepted, and verified-good states.

### Neutral

- **Anodized Ground** (`colors.ground`): the page and sticky header plane.
- **Instrument Panel** (`colors.panel`): camera index, main stage, rail, tables, sequences, and policy surfaces.
- **Raised Steel Tone** (`colors.panel-2`): hover and focused-row tonal change; it does not imply physical elevation.
- **Internal Steel Rule** (`colors.steel`): cell dividers and secondary separators.
- **Structural Rule** (`colors.line`): panel boundaries, header divisions, and primary outlines.
- **Muted Reading** (`colors.muted`): explanatory copy and secondary operational labels.
- **Faint Engraving** (`colors.faint`): metadata, empty readings, and low-priority annotations.
- **Measured Ink** (`colors.ink`): primary labels, values, and titles.

### Named Rules

**The Signal Economy Rule.** Calibration cyan marks focus, selection, route, or active inference; it is not ambient decoration.

**The Redundant State Rule.** Operational state always has a text label, symbol, border, or placement cue in addition to color.

**The No Spectacle Color Rule.** Gradients, neon, rainbow accents, pastel surfaces, and decorative color effects are forbidden.

## Typography

**Display Font:** Bahnschrift (with Segoe UI and generic sans-serif fallbacks)  
**Body Font:** Segoe UI (with Arial and generic sans-serif fallbacks)  
**Label/Mono Font:** Cascadia Mono (with Consolas and generic monospace fallbacks)

**Character:** Bahnschrift gives camera titles and instrument headings a compact engineered silhouette. Segoe UI keeps explanatory language neutral, while Cascadia Mono turns identifiers, ranks, timestamps, measurements, and compact labels into calibrated readings.

These are system-dependent stacks. No font files are bundled, and the denied self-hosted font installation remains an implementation constraint; agents must not imply cross-platform metric parity or silently introduce a web-font dependency.

### Hierarchy

- **Display** (semibold, responsive 23–34px, tight tracking): the focused camera name and no larger decorative headline.
- **Headline** (semibold, 13–15px): section and evidence headings, capacity verdicts, and resident model identifiers.
- **Body** (regular, predominantly 11px): explanations, locations, reasons, and evidence boundaries; long evidence copy is constrained to 72 characters and uses generous line-height.
- **Data** (medium or semibold, 9–18px): values, camera IDs, route nodes, scores, timestamps, and decision IDs.
- **Label** (semibold, 11px, uppercase, tracked): engraved instrument labels, header readings, table headings, and state labels.

### Named Rules

**The Instrument Label Rule.** Uppercase mono labels identify equipment and state; sentence-case sans text explains meaning.

**The No Hero Type Rule.** Type supports the operating surface; no oversized marketing headline may displace live mechanism or evidence.

## Layout

The wide operating bench is a centered grid capped at 1760px with 18px outer padding and 14px gutters. Its primary columns are a 210px camera index, a fluid measured-feed stage with a 560px minimum, and a 300px instrumentation rail. The index and rail flank the live feed; camera array, candidate field, decision sequence, policy matrix, and evidence then run in a clear vertical order. The 58px system header remains sticky, while the camera index stays pinned 76px from the viewport top.

The measured feed changes from a wide 16:5.4 working aperture above 980px to 16:6.8 through the intermediate layout and 16:10 on small screens. Its six readings form one row when space permits and a three-by-two grid below 1300px. Above 720px, compact camera feeds use a shallow 16:4.2 strip and suppress their duplicate metrics; at mobile width, those metrics return beside a 130px video column.

At 1300px and below, header navigation and the decision-ID instrument are removed, the flanking columns contract to 185px and 275px, and the central minimum becomes 480px. At 980px and below, the page becomes a 170px camera-index plus main-stage grid; the instrumentation rail moves below the feed as two columns, while the last two candidate-table fields are hidden. At 720px and below, the operations surface uses a 10px padded single-column flow: the camera index becomes a three-across selector, control buttons span the available width, the rail and policy matrix stack, the candidate table becomes labeled two-column records, evidence stacks, and the footer turns vertical.

**The Mechanism-First Rule.** Camera selection, measured feed, dispatch, capacity, candidate ordering, and operator control must remain ahead of policy explanation and historical evidence.

## Elevation & Depth

This is a planar, no-drop-shadow system. Depth comes from adjacent graphite tones, one-pixel steel boundaries, nested data cells, sticky positioning, and density changes. The only `box-shadow` usage is a two-pixel inset cyan rule on focused or selected items; it is a state index, not simulated elevation. Panels never float above the bench, and hover uses a tonal shift or border change rather than lift.

### Named Rules

**The Planar Bench Rule.** Do not add ambient shadows, glow, blur, glass, or lifted-card depth; use rules and tonal planes.

**The Inset State Rule.** A two-pixel cyan inset edge may mark the current camera, candidate, or compact feed, but it never becomes a decorative shadow vocabulary.

## Shapes

All operational surfaces are square (`rounded.square`). Panels, controls, camera letters, route nodes, state marks, detection boxes, meters, and table cells use hard corners and one-pixel rules. Right-angle reticle corners frame the measured feed, and detection regions use thin rectangular boxes with small indexed labels. Icons are restrained outline glyphs, generally 13–20px, paired with text rather than used as ornamental badges.

The recurring silhouette is a measured rectangular aperture subdivided by steel rules. Pills, circular floating actions, exaggerated radius, organic containers, and decorative blobs do not belong in this system.

## Components

### System Header and Navigation

- **Structure:** A sticky 58px graphite bar with a 230px wordmark zone at full width, central anchor navigation, and right-aligned node, cadence, connection, and decision readings.
- **State:** Navigation hover changes text and reveals a bottom rule. Connection states combine a square marker with explicit live, stale, connecting, disconnected, degraded, or static text.
- **Responsive:** Navigation disappears at 1300px; individual header readings disappear at 980px, leaving the wordmark and connection state.

### Camera Index

- **Structure:** A narrow sticky rail of 74px rows, each with a square camera letter, name, operating-mode reading, count, and optional override or inference flags.
- **Focused:** The row shifts to the second panel tone and receives a two-pixel cyan inset edge; `aria-pressed` exposes the same selection semantically.
- **Active:** The camera letter changes to bright cyan. Focused camera and runtime-selected camera are related but not conflated.
- **Responsive:** At 720px the rail becomes a three-column selector, drops the legend and flag column, and allows camera names to wrap.

### Measured Feed and Measurement Strip

- **Structure:** A desaturated, contrast-raised camera aperture with right-angle reticles, frame coordinates, source/task quality, inference tally, and mapped detection boxes.
- **State:** Active inference brightens the tally border and marker. Observation-only video remains visible at reduced opacity. Missing mapped media becomes an explicit `NO LOCAL FEED` state.
- **Measurements:** People, inference time, utility, support, wait, and priority remain attached as divided mono cells beneath the feed; absent data renders an em dash.

### Operator Control Buttons

- **Primary:** The square control uses a dark blue-steel fill, cyan border and text, a 34px height, and compact icon-label alignment.
- **Hover / Focus:** Hover changes only the tonal fill. Keyboard focus uses the global two-pixel bright-cyan outline with a three-pixel offset.
- **Release:** Active override changes to an amber border and text on a brown-black plane so destructive release reads differently from acquisition.
- **Disabled / Busy:** Disconnected or applying controls use 42% opacity and a non-interactive cursor; busy copy explicitly reads `Applying control…`.
- **Error:** Failure appears inline with an alert icon, fault-colored border and surface, a recovery instruction, and `role="alert"`.

### Instrumentation Rail

- **Structure:** Four divided sections for current dispatch, resident model, capacity admission, and focused policy. Each uses an engraved icon label followed by data-definition rows.
- **Dispatch:** A literal camera-to-model route diagram precedes the human-readable scheduler reason and exact decision metadata.
- **Capacity:** Admission is a text verdict paired with a five-pixel linear meter and protected/available/GPU readings. Violations appear as a separate fault block.
- **Responsive:** The rail becomes a two-column instrument bank below 980px and a single vertical stack below 720px.

### Compact Camera Array

- **Structure:** Three shallow camera apertures repeat camera ID, name, selection/eligibility state, and—only at mobile width—people, utility, wait, and rank metrics.
- **Focused / Active:** Focus uses a cyan border; current dispatch adds a two-pixel inset top rule and explicit `SELECTED` copy.
- **Unavailable:** A square `NO FEED` field replaces video without inventing a healthy frame.

### Scheduler Candidate Field

- **Structure:** A nine-column policy-first table for rank, camera, class, mode, utility, wait, score, eligibility, and reason. Each candidate row is a button that moves inspection focus.
- **Selected:** The selected candidate uses a darker cyan-black row and a two-pixel inset cyan edge.
- **Responsive:** Eligibility and reason are suppressed only in the intermediate two-column layout; at mobile width every field returns as a labeled two-column record, with reason spanning both columns.
- **Empty:** The table states that no scheduler decision has arrived and explains when it will populate.

### Decision Sequence

- **Structure:** A horizontally scrollable strip of up to twelve retained decisions, each showing time, camera, name, decision class, reason, and decision ID.
- **Current:** The newest record receives the selected tonal plane and a cyan timeline rule. Empty history reads `AWAITING LIVE DECISION SEQUENCE`.

### State Marks, Policy, and Evidence

- **State Marks:** A square outlined marker and uppercase label combine neutral, active/good, warning, or bad semantics; no state is a color-only dot.
- **Policy:** Three inspect-only policy columns expose configuration and overrides without mutation controls. Fixture and disabled states are plainly labeled.
- **Evidence:** A restrained rule-bounded panel states the evaluation boundary in prose and places three frozen scores in a ruled comparison; the best result uses a muted green plane, not celebratory decoration.

## Do's and Don'ts

### Do:

- **Do** preserve the Optical Metrology Bench sequence: camera index, measured feed, dispatch/capacity rail, camera array, candidate field, decision sequence, policy, then evidence.
- **Do** use square geometry, one-pixel steel rules, compact mono readings, and desaturated measured video as the durable instrument language.
- **Do** distinguish focused inspection, selected dispatch, active inference, eligibility, connection phase, fixture use, stale data, capacity rejection, and unavailable data with explicit language.
- **Do** keep keyboard focus visible with the two-pixel cyan outline and three-pixel offset on every interactive anchor and button.
- **Do** preserve the truthful empty and unconfirmed states and the inspect-only camera-policy boundary.
- **Do** treat the Bahnschrift, Segoe UI, Cascadia Mono, and Consolas stacks as system-dependent until an approved bundled-font strategy exists.

### Don't:

- **Don't** introduce gradients, rainbow or neon color, pastel palettes, radial orbs, dot-grid backgrounds, sparkles, emojis, or generic AI decoration.
- **Don't** use liquid glass, backdrop blur, ambient glow, large shadows, lifted cards, bento grids, or excessive rounded containers.
- **Don't** turn the interface into a terminal window, marketing page, fake demo, pricing surface, testimonial wall, social-proof module, or checklist pitch.
- **Don't** add excessive pills, decorative arrows, oversized type, excessive hover motion, or ornamental animation.
- **Don't** invent healthy runtime values, hide unavailable states, imply policy mutation, or overstate detector and learned-SAGE evidence.
- **Don't** install or substitute a hosted display font without resolving the current denied self-hosting constraint and verifying projected-laptop metrics.
