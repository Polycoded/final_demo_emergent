"""Reference-only CPU inference for the frozen Review-1 scalar router."""
from __future__ import annotations
import math
from pathlib import Path
import joblib

FEATURE_NAMES=("person_count","occupancy_ratio","confidence_mean","confidence_variance","count_delta","motion_energy","blur","blockiness","frame_age_ms","queue_depth","accelerator_utilization","expert_load")
def clip(x): return max(0.,min(1.,float(x)))
def transform(raw):
 if set(raw)!=set(FEATURE_NAMES): raise ValueError('Exactly the 12 documented feature names are required')
 if any(not math.isfinite(float(v)) for v in raw.values()): raise ValueError('Features must be finite')
 return [clip(max(0,float(raw['person_count']))/40),clip(raw['occupancy_ratio']),clip(raw['confidence_mean']),clip(raw['confidence_variance']),clip(abs(raw['count_delta'])/40),clip(raw['motion_energy']),clip(raw['blur']),clip(raw['blockiness']),clip(raw['frame_age_ms']/2000),clip(raw['queue_depth']/10),clip(raw['accelerator_utilization']),clip(raw['expert_load'])]
def load(path: str|Path): return joblib.load(path)
def predict(model,raw): return float(model.predict([transform(raw)])[0])
