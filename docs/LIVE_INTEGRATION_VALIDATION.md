# Live integration validation

Date: 2026-08-29

The final integration was exercised locally with three independent video
workers using `feed-a-clear.avi`, `feed-b-degraded.avi`, and
`feed-c-temporal.avi`. Every worker ran YOLOX Nano; the coordinator ranked one
three-feed decision window at a time; only the selected worker ran YOLOX Tiny.
Both ONNX models used the DirectML execution provider.

## Final run

- Completed decision windows: **24**
- Windows containing all three feeds: **24 / 24**
- Heavyweight calls: **24**
- Completed heavyweight calls: **24**
- Failures: **0**
- Timeouts: **0**
- Token-budget violations: **0**
- Selected feeds: A = 6, B = 0, C = 18
- Unique observed feature vectors per feed: A = 5, B = 5, C = 5
- Occupancy range: **0.01962–0.04344**
- Mean occupancy: **0.03309**
- Router checkpoint SHA-256:
  `a098669583c43b93796f0d0fed1d1581183bada5c3852def14cbe74239dc8509`

The run verifies complete window formation, real Nano/Tiny inference, corrected
YOLOX grid/stride decoding, original-pixel occupancy, exclusive deep-call lease
handling, persistence, and execution completion. Feed B was not selected in
this short scenario because its predicted utility never ranked first; this is
reported rather than treated as a fairness claim.

## Automated verification

- Backend: 18 tests passed.
- Ruff: passed.
- Frontend production build: passed.
- Docker Compose configuration: passed with a supplied API key.
- Docker image build was not run because Docker Desktop was not active.

These are local integration results. The separate 192-window Review-1 report
remains the source for comparative policy claims; this smoke run must not be
presented as a new detector-accuracy or baseline-comparison experiment.
