# Scalar router interface contract

The model input is a **12-element transformed float vector** in exactly this order:

1. `person_count`: `clip(raw / 40, 0, 1)`
2. `occupancy_ratio`: `clip(raw, 0, 1)`; union of valid original-pixel Nano boxes / original frame area
3. `confidence_mean`: `clip(raw, 0, 1)`
4. `confidence_variance`: `clip(raw, 0, 1)`
5. `count_delta`: `clip(abs(raw) / 40, 0, 1)` within one camera/session only
6. `motion_energy`: `clip(raw, 0, 1)` within one camera/session only
7. `blur`: `clip(raw, 0, 1)`; 1 means more degraded
8. `blockiness`: `clip(raw, 0, 1)`; 1 means more degraded
9. `frame_age_ms`: `clip(raw / 2000, 0, 1)`
10. `queue_depth`: `clip(raw / 10, 0, 1)`
11. `accelerator_utilization`: `clip(raw, 0, 1)`
12. `expert_load`: `clip(raw, 0, 1)`

The model returns one scalar: predicted Tiny-over-Nano **proxy utility**. Higher ranks ahead of lower values. It does not return four specialist scores.

For a window of candidate camera feeds, calculate each feed’s feature vector, predict each scalar, and rank descending. Tie-break deterministically by longest wait, then lexicographically smallest camera ID. The scheduler—not this model—must grant exactly one global Tiny token.

Reject missing, NaN, or infinite feature values. Clamp only the specified finite values. Do not reorder features or apply unrecorded normalization.

Example Python loading:

```python
import joblib
router = joblib.load("model/router-review1-v2.joblib")
utility = float(router.predict([transformed_feature_vector])[0])
```

This is an offline Review-1 candidate only. Preserve a deterministic fallback policy and do not claim the proxy utility is detection accuracy.
