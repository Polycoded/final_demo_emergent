# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The primary user for this surface is a hackathon judge watching a live, presenter-led demonstration on one laptop. The interface must also remain credible as an operator-facing edge computer-vision control surface rather than becoming a marketing presentation.

## Product Purpose

CAHMA Control demonstrates and operates a local edge-computing system that shares constrained resident inference capacity across multiple camera feeds. It makes camera policy, protected service, adaptive scheduling, model dispatch, live inference, capacity, and decision evidence visible in one place. Success means a judge can understand that the backend is making real, policy-governed allocation decisions while those decisions and operator overrides are visibly reflected in the live dashboard.

## Positioning

CAHMA decides which potential inference call is worth creating before compute is granted. Safety requirements, active policy, manual overrides, minimum service, model readiness, capacity, waiting time, and fairness constrain the decision; adaptive utility ranks only the work that remains eligible. Every allocation produces an inspectable decision receipt.

## Operating Context

- A presenter runs the dashboard, FastAPI runtime, three labelled camera scenarios, scheduler worker, and resident ONNX model locally on one laptop.
- Judges view three camera feeds and a deliberate live scheduling cadence while the presenter activates or releases a manual override.
- Raw frames and inference remain local. Compact observations, scheduler decisions, inference events, capacity reports, and receipts drive the interface.
- The strongest evidence is an equal-budget person-routing evaluation plus a working policy-protected v2 orchestration runtime. Cross-task learned SAGE remains future work.

## Capabilities and Constraints

- React 19 and Vite frontend with a FastAPI backend.
- Live events arrive over the existing `/v1/events` WebSocket connection.
- Existing camera override behavior and all backend contracts must be preserved.
- Camera policies are inspect-only in this redesign. The dashboard must not add policy mutation controls.
- The runtime exposes camera policies, overrides, resident models, capacity admission, scheduling decisions, inference results, telemetry, receipts, health, readiness, metrics, and formal evaluation runs.
- The main demonstration uses three local recorded camera feeds, but the interface should not encode misleading healthy states when runtime data is absent.
- The interface must distinguish connected, connecting, disconnected, stale, unavailable, rejected, degraded, empty, and active states where the available data supports them.

## Brand Commitments

- Product name: **CAHMA Control**.
- Runtime and evaluation identity: **CAHMA Arena v2**.
- The product must read as an industrial AI and edge-computing control center, not a generic AI SaaS site.
- The visual language must be clean, technical, restrained, functional, and credible.
- Avoid gradients, rainbow or neon color, emojis, sparkles, liquid glass, bento grids, radial orbs, dot-grid backgrounds, terminal-window aesthetics, fake testimonials, pricing tiers, marketing checklists, excessive pills, excessive rounded cards, large shadows, pastel palettes, decorative arrows, excessive hover animation, fake demos, social proof, and generic AI decoration.

## Evidence on Hand

- Three local labelled demonstration feeds under `public/feeds/`.
- Frozen evaluation results and provenance under `evidence/`.
- Review and implementation documentation under `docs/`.
- A resident YOLOX Tiny ONNX model and trained Review-1 scalar-router checkpoint under `backend/`.
- The interface must not imply heterogeneous learned-SAGE proof or production detector accuracy beyond the evidence documented in the repository.

## Product Principles

1. Show the live mechanism before explaining it.
2. Make policy, eligibility, scheduling, inference, and capacity visibly distinct.
3. Never present unavailable or inferred data as a healthy confirmed state.
4. Preserve operator control and auditable reasoning without compromising safety policy.
5. Use evidence precisely and state evaluation boundaries plainly.

## Accessibility & Inclusion

The projected laptop demo must remain legible at normal browser zoom. Operational state cannot rely on color alone, interactive controls require visible keyboard focus, and the layout must remain usable at narrow laptop and mobile widths.
