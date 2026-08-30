from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class FeedState(StrEnum):
    OBSERVE = "OBSERVE"
    CANDIDATE = "CANDIDATE"
    DEEP_INSPECT = "DEEP_INSPECT"
    COOLDOWN = "COOLDOWN"


class FrameFeatures(BaseModel):
    feed_id: str
    captured_at: datetime
    person_count: int = Field(ge=0)
    confidence_mean: float = Field(ge=0, le=1)
    confidence_variance: float = Field(ge=0, le=1)
    occupancy_ratio: float = Field(ge=0, le=1)
    count_delta: float = Field(ge=0)
    motion_energy: float = Field(ge=0, le=1)
    blur: float = Field(ge=0, le=1)
    blockiness: float = Field(ge=0, le=1)
    frame_age_ms: float = Field(ge=0)
    queue_depth: int = Field(ge=0)
    accelerator_utilization: float | None = Field(default=None, ge=0, le=1)
    expert_load: float = Field(default=0, ge=0, le=1)


class GateResult(BaseModel):
    scores: dict[str, float]
    selected: list[str]
    utility: float


class DecisionReceipt(BaseModel):
    receipt_id: str
    timestamp: datetime
    feed_id: str
    previous_state: FeedState
    next_state: FeedState
    policy: str
    shared_features: FrameFeatures
    gate: GateResult
    token_available: bool
    deep_call_executed: bool
    reason: str
    decision_latency_ms: float


class FeedSnapshot(BaseModel):
    feed_id: str
    state: FeedState
    gate: GateResult | None = None
    latest: FrameFeatures | None = None


class RuntimeSnapshot(BaseModel):
    generated_at: datetime
    token_owner: str | None
    feeds: list[FeedSnapshot]
    recent_receipts: list[DecisionReceipt]


class RankedFeed(BaseModel):
    feed_id: str
    predicted_proxy_utility: float
    wait_windows: int
    rank: int


class WindowRoutingDecision(BaseModel):
    timestamp: datetime
    selected_feed_id: str
    model: str
    model_sha256: str | None = None
    rankings: list[RankedFeed]
    reason: str


class CoordinatedRoutingResponse(BaseModel):
    window_id: str
    call_id: str
    selected: bool
    selected_feed_id: str
    decision: WindowRoutingDecision


class DeepExecutionReport(BaseModel):
    call_id: str
    inference_ms: float = Field(ge=0)
    error: str | None = None
