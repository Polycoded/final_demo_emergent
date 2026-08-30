from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class CameraMode(StrEnum):
    SAFETY = "SAFETY"
    PRIORITY = "PRIORITY"
    ADAPTIVE = "ADAPTIVE"
    CONTEXTUAL = "CONTEXTUAL"


class TaskId(StrEnum):
    PPE = "PPE"
    PERSON = "PERSON"
    CROWD = "CROWD"
    VEHICLE = "VEHICLE"
    INTRUSION = "INTRUSION"
    GENERAL_OBJECT = "GENERAL_OBJECT"


class ScheduleRule(BaseModel):
    start: str
    end: str
    mode: CameraMode
    days: list[int] = Field(default_factory=lambda: list(range(7)))


class CameraPolicy(BaseModel):
    camera_id: str = Field(min_length=1, max_length=64)
    camera_name: str = Field(min_length=1, max_length=120)
    location: str = Field(default="", max_length=200)
    task_id: TaskId
    model_id: str = Field(min_length=1, max_length=120)
    operating_mode: CameraMode
    priority: int = Field(default=3, ge=1, le=5)
    timezone: str = "Asia/Calcutta"
    schedule: list[ScheduleRule] = Field(default_factory=list)
    safety_requirement: bool = False
    minimum_deep_rate_fps: float = Field(default=0, ge=0)
    maximum_deep_rate_fps: float = Field(default=5, gt=0)
    maximum_wait_ms: int = Field(default=3000, ge=1)
    fallback_policy: str = "priority_age"
    enabled: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> CameraPolicy:
        if self.minimum_deep_rate_fps > self.maximum_deep_rate_fps:
            raise ValueError("minimum_deep_rate_fps cannot exceed maximum_deep_rate_fps")
        if self.operating_mode == CameraMode.SAFETY:
            self.safety_requirement = True
            if self.minimum_deep_rate_fps <= 0:
                raise ValueError("SAFETY cameras require a positive minimum_deep_rate_fps")
        return self


class ManualOverrideRequest(BaseModel):
    duration_seconds: int | None = Field(default=30, ge=1, le=86400)
    reason: str = Field(default="Operator requested protected inference", max_length=300)


class ActiveOverride(BaseModel):
    camera_id: str
    created_at: datetime
    expires_at: datetime | None
    reason: str


class ObserverSignals(BaseModel):
    camera_id: str
    task_id: TaskId
    captured_at: datetime
    motion: float = Field(ge=0, le=1)
    frame_difference: float = Field(ge=0, le=1)
    blur: float = Field(ge=0, le=1)
    brightness: float = Field(ge=0, le=1)
    contrast: float = Field(ge=0, le=1)
    entropy: float = Field(ge=0, le=1)
    scene_change: float = Field(default=0, ge=0, le=1)
    time_since_deep_ms: float = Field(default=0, ge=0)
    previous_count: int | None = Field(default=None, ge=0)
    previous_confidence: float | None = Field(default=None, ge=0, le=1)
    queue_depth: int = Field(default=0, ge=0)
    gpu_utilization: float = Field(default=0, ge=0, le=1)


class ModelSpec(BaseModel):
    model_id: str
    task_id: TaskId
    path: str
    execution_provider: str = "CPUExecutionProvider"
    required_vram_mb: float = Field(default=0, ge=0)
    safe_throughput_fps: float = Field(default=0, ge=0)
    resident: bool = False
    warmed: bool = False
    load_events: int = 0


class ResidentInferenceRequest(BaseModel):
    camera_id: str
    decision_id: str | None = None
    frame_base64: str = Field(min_length=1)


class CapacityReport(BaseModel):
    accepted: bool
    protected_required_fps: dict[str, float]
    model_safe_fps: dict[str, float]
    violations: list[str]


class V2Candidate(BaseModel):
    camera_id: str
    task_id: TaskId
    operating_mode: CameraMode
    decision_class: str
    sage_utility: float = Field(ge=0, le=1)
    sage_confidence: float = Field(ge=0, le=1)
    priority: int
    wait_ms: float = Field(ge=0)
    scheduler_score: float
    eligible: bool
    reason_code: str
    rank: int = 0


class V2SchedulingDecision(BaseModel):
    decision_id: str
    timestamp: datetime
    selected_camera_id: str
    selected_model_id: str
    decision_class: str
    sage_model: str
    fallback_used: bool
    reason_code: str
    candidates: list[V2Candidate]


class V2RuntimeSnapshot(BaseModel):
    generated_at: datetime
    runtime_version: str = "v2"
    cameras: list[CameraPolicy]
    overrides: list[ActiveOverride]
    models: list[ModelSpec]
    capacity: CapacityReport
    recent_decisions: list[V2SchedulingDecision]
