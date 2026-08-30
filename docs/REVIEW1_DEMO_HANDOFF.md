# Review-1 demo handoff

## A. Minimal architecture

Three local video sources feed lightweight OpenCV observation signals to the policy engine. The capacity guard verifies protected commitments against the warmed resident YOLOX-Tiny service. The scheduler applies safety, override, minimum-service, priority, adaptive utility and fairness rules in that order. The selected camera alone receives production inference. The API stores the receipt and streams the decision to the React dashboard.

## B. Validation reuse

The v2 prototype reuses the frozen person-routing artefact and its Review-1 holdout results only in the separately labelled evidence section. The live v2 policy path adds policy precedence, capacity admission, resident model management and deterministic adaptive scheduling. These additions do not turn the older result into heterogeneous SAGE evidence. The live selector truthfully reports `deterministic-observer-v2-baseline` and `fallback_used=true`.

## C. Build and validation log

Validated on 2026-08-30:

- `run-demo.bat --check`: PASS; Python, npm, dependencies, model and video prerequisites found.
- Backend: PASS; 24 tests passed. Two non-failing environment warnings were emitted by Starlette/joblib.
- Frontend: PASS; Vite production build completed.
- Dashboard: PASS; HTTP 200 at `http://127.0.0.1:5173/`.
- Runtime: PASS; three cameras, one model and admitted protected capacity reported.
- Override lifecycle: PASS; Camera B override accepted and released.
- Policy precedence: PASS; a due Camera A safety commitment correctly remained ahead of the Camera B override at the sampled instant.
- Browser rehearsal: PASS; the live development dashboard rendered, exposed all three controls, displayed `0.2 FPS` protected demand and `12 FPS` safe capacity, and returned to zero active overrides after the scripted interaction.

## D. Three end-to-end receipts

| Run | Receipt | Selected | Class | Reason | Model | Capacity |
|---|---|---|---|---|---|---|
| 1 | `V2-C8F87348C9` | Camera A | PROTECTED | SAFETY_REQUIREMENT | person-yolox-tiny | Admitted |
| 2 | `V2-340690ED9C` | Camera B | ADAPTIVE | DETERMINISTIC_PRIORITY_AGE_BASELINE | person-yolox-tiny | Admitted |
| 3 | `V2-711B07AB47` | Camera A | PROTECTED | SAFETY_REQUIREMENT | person-yolox-tiny | Admitted |

These IDs are local runtime receipts, not benchmark claims. Generated runtime evidence is excluded from Git by design.

## E. Three-minute demo script

1. **Problem (20 seconds):** “Running the largest model continuously on every camera is increasingly expensive in memory and compute. CAHMA shares one resident production model without treating every feed identically.”
2. **Policies (35 seconds):** Point to the three modes and the hierarchy. Explain that safety and guaranteed service are constraints, not optional scores.
3. **Live decision (40 seconds):** Show utility and confidence beside final rank. Point out that the final decision can differ because policy and waiting time are applied after observation.
4. **Resident capacity (25 seconds):** Show the warmed model, one load event and admission-control comparison. Explain that protected work is rejected if the system cannot honor it.
5. **Override (30 seconds):** Select “Take control” on Camera B. Show the override state and explain that safety work due at that exact instant still retains precedence; release the override.
6. **Receipt (25 seconds):** Read the selected route, decision class, reason code, model and scheduler rank.
7. **Evidence boundary (25 seconds):** Show the Review-1 table. State that it validates the earlier learned person router, while today’s v2 policy layer is a deterministic, auditable baseline awaiting cross-task SAGE training.

## F. Known limitations

- All three current demo tasks use person detection; heterogeneous task models are architecture-ready but not yet trained and validated.
- The v2 adaptive selector is deterministic rather than a trained cross-task SAGE selector.
- Review-1 learned-router evidence applies only to the earlier frozen person-routing evaluation.
- Demo videos are controlled local footage and are not a live camera deployment.
- The default demo API key is local-only and must never be used for network deployment.

## G. Local setup

Run `npm install`, install `backend` with `python -m pip install -e ".[dev]"`, then execute `run-demo.bat`. Keep the dashboard at 100% browser zoom. If port 8080 is occupied by an unrelated process, stop that process instead of starting a second backend. Keep this report open as the fallback narration and capture a local screen recording before judging.
