# CAHMA Arena v2 — final-round prototype

This folder is the self-contained final-round demo package. It contains the current React dashboard, FastAPI runtime, v2 policy scheduler, resident YOLOX-Tiny model, frozen learned-router checkpoint, three local demo scenarios, tests, evidence and presentation documentation.

## Quick start on Windows

Requirements: Python 3.11 or 3.12, Node.js/npm and Windows 10/11.

```powershell
cd final-round-prototype
npm install
cd backend
python -m pip install -e ".[dev]"
cd ..
.\run-demo.bat
```

Open `http://127.0.0.1:5173/`. The launcher uses ports `8080` and `5173` and opens three labelled terminal windows: backend, dashboard and v2 driver.

To validate without starting services:

```powershell
.\run-demo.bat --check
.\VERIFY_PACKAGE.ps1
npm run build
cd backend
python -m pytest -q
```

## Included runtime

- `src/` — v2 React orchestration dashboard.
- `public/feeds/` — browser-compatible copies of the three demo feeds.
- `backend/app/` — API, policy engine, observer, scheduler, model pool and driver.
- `backend/assets/scenarios/` — analyzed AVI sources used by the v2 driver.
- `backend/models/yolox_tiny.onnx` — resident production-inference model.
- `backend/checkpoints/router-review1-v2.joblib` — frozen learned person-router checkpoint.
- `backend/tests/` — backend verification suite.
- `evidence/` — frozen Review-1 metrics, provenance and integration contract.
- `docs/` and `PITCH.md` — final-review pitch, demo flow, architecture, Q&A and limitations.

## Start here for the review

1. Read `PITCH.md`.
2. Follow `docs/FINAL_ELIMINATION_REVIEW.md`.
3. Keep `docs/REVIEW1_DEMO_HANDOFF.md` open as the fallback.
4. Use `evidence/reports/review1-results.json` for exact measured numbers.

## Evidence boundary

The frozen learned person router achieved `+35.06%` proxy utility over round robin and `+33.34%` over confidence-only on a deterministic 192-window, equal-budget simulated replay. This is Nano-to-Tiny teacher-disagreement proxy utility—not detector accuracy, mAP, incident prevention or production compute savings.

The live v2 policy scheduler is explicitly identified as `deterministic-observer-v2-baseline`. It demonstrates policy protection, capacity admission, resident inference, fairness, manual overrides and auditable receipts; it is not presented as a trained heterogeneous SAGE model.

## Local-only security

The launcher uses the demo key `hackathon-demo-key` and binds services to `127.0.0.1`. Do not expose this configuration to a network. Generated databases, logs, caches and runtime evidence are ignored.
