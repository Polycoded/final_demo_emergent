from __future__ import annotations

from datetime import UTC, datetime, timedelta
from threading import RLock
from uuid import uuid4

from .camera_policy import CameraPolicyEngine
from .model_pool import ResidentModelPool
from .v2_schemas import (
    CameraMode,
    ObserverSignals,
    V2Candidate,
    V2SchedulingDecision,
)


class V2Scheduler:
    """Policy-first scheduler. SAGE is optional and never controls protected correctness."""

    def __init__(
        self,
        policies: CameraPolicyEngine,
        models: ResidentModelPool,
        minimum_adaptive_dwell_seconds: float = 6.0,
    ) -> None:
        self.policies = policies
        self.models = models
        self.minimum_adaptive_dwell = timedelta(
            seconds=max(0.0, minimum_adaptive_dwell_seconds)
        )
        self.recent: list[V2SchedulingDecision] = []
        self.last_selected_camera_id: str | None = None
        self.last_selected_at: datetime | None = None
        self._lock = RLock()

    @staticmethod
    def observer_utility(signals: ObserverSignals) -> tuple[float, float]:
        """Documented deterministic v2 baseline until task-conditioned SAGE is trained."""
        age = min(1.0, signals.time_since_deep_ms / 5000.0)
        quality_change = max(signals.blur, abs(signals.brightness - 0.5) * 2)
        utility = min(
            1.0,
            0.34 * signals.motion
            + 0.24 * signals.frame_difference
            + 0.14 * signals.scene_change
            + 0.18 * age
            + 0.10 * quality_change,
        )
        # This is support confidence, not learned predictive confidence.
        confidence = 0.85 if signals.entropy > 0.05 else 0.45
        return utility, confidence

    def schedule(
        self, observations: list[ObserverSignals], now: datetime | None = None
    ) -> V2SchedulingDecision:
        if not observations:
            raise ValueError("At least one observation is required")
        current = now or datetime.now(UTC)
        seen: set[str] = set()
        candidates: list[V2Candidate] = []
        for signals in observations:
            if signals.camera_id in seen:
                raise ValueError(f"Duplicate camera observation: {signals.camera_id}")
            seen.add(signals.camera_id)
            policy = self.policies.get(signals.camera_id)
            if not policy.enabled:
                continue
            if signals.task_id != policy.task_id:
                raise ValueError(f"Task mismatch for camera {signals.camera_id}")
            mode = self.policies.effective_mode(policy, current)
            override = self.policies.has_override(policy.camera_id, current)
            safety_due_ms = (
                1000.0 / policy.minimum_deep_rate_fps
                if policy.minimum_deep_rate_fps > 0
                else 0
            )
            safety_due = mode == CameraMode.SAFETY and (
                signals.time_since_deep_ms >= safety_due_ms
            )
            protected = safety_due or override
            utility, confidence = self.observer_utility(signals)
            wait_ratio = min(1.0, signals.time_since_deep_ms / policy.maximum_wait_ms)
            if protected:
                decision_class = "PROTECTED"
                reason = "MANUAL_OVERRIDE" if override else "SAFETY_REQUIREMENT"
                score = 10_000 + policy.priority * 100 + wait_ratio
            elif mode == CameraMode.SAFETY:
                decision_class = "PROTECTED"
                reason = "PROTECTED_RATE_SATISFIED"
                score = -1
            else:
                decision_class = "ADAPTIVE"
                reason = "DETERMINISTIC_PRIORITY_AGE_BASELINE"
                priority = (policy.priority - 1) / 4
                context_bonus = 0.10 if mode == CameraMode.PRIORITY else 0.0
                score = 0.55 * utility + 0.25 * priority + 0.20 * wait_ratio + context_bonus
            try:
                model = self.models.get(policy.model_id)
                model_ready = model.resident and model.warmed
                eligible = model_ready and not (
                    mode == CameraMode.SAFETY and not protected
                )
                if not model_ready:
                    reason = "MODEL_NOT_RESIDENT"
            except KeyError:
                eligible = False
                reason = "MODEL_NOT_REGISTERED"
            candidates.append(
                V2Candidate(
                    camera_id=policy.camera_id,
                    task_id=policy.task_id,
                    operating_mode=mode,
                    decision_class=decision_class,
                    sage_utility=utility,
                    sage_confidence=confidence,
                    priority=policy.priority,
                    wait_ms=signals.time_since_deep_ms,
                    scheduler_score=score,
                    eligible=eligible,
                    reason_code=reason,
                )
            )
        eligible = [item for item in candidates if item.eligible]
        if not eligible:
            raise ValueError("No observation has an eligible resident production model")
        ordered = sorted(
            candidates,
            key=lambda item: (
                not item.eligible,
                -item.scheduler_score,
                -item.wait_ms,
                item.camera_id,
            ),
        )
        protected = [
            item for item in ordered if item.eligible and item.decision_class == "PROTECTED"
        ]
        selected = protected[0] if protected else next(item for item in ordered if item.eligible)
        if not protected and self.last_selected_camera_id and self.last_selected_at:
            dwell_active = current - self.last_selected_at < self.minimum_adaptive_dwell
            previous = next(
                (
                    item
                    for item in ordered
                    if item.camera_id == self.last_selected_camera_id and item.eligible
                ),
                None,
            )
            if dwell_active and previous is not None:
                selected = previous
                selected.reason_code = "ADAPTIVE_DWELL_HOLD"
        ordered = [selected, *(item for item in ordered if item is not selected)]
        for rank, candidate in enumerate(ordered, start=1):
            candidate.rank = rank
        policy = self.policies.get(selected.camera_id)
        decision = V2SchedulingDecision(
            decision_id=f"V2-{uuid4().hex[:10].upper()}",
            timestamp=current,
            selected_camera_id=selected.camera_id,
            selected_model_id=policy.model_id,
            decision_class=selected.decision_class,
            sage_model="deterministic-observer-v2-baseline",
            fallback_used=True,
            reason_code=selected.reason_code,
            candidates=ordered,
        )
        with self._lock:
            if selected.camera_id != self.last_selected_camera_id:
                self.last_selected_camera_id = selected.camera_id
                self.last_selected_at = current
            self.recent.insert(0, decision)
            del self.recent[50:]
        return decision

    def recent_decisions(self) -> list[V2SchedulingDecision]:
        with self._lock:
            return list(self.recent)
