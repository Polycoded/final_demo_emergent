"""Deterministic, auditable sparse router. All scores are explicit on purpose."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import uuid4

from .gate import LearnedGate
from .scalar_router import ScalarUtilityGate
from .schemas import (
    DecisionReceipt,
    FeedSnapshot,
    FeedState,
    FrameFeatures,
    GateResult,
    RankedFeed,
    RuntimeSnapshot,
    WindowRoutingDecision,
)


@dataclass
class FeedRuntime:
    state: FeedState = FeedState.OBSERVE
    latest: FrameFeatures | None = None
    gate: GateResult | None = None
    state_since: datetime | None = None
    cooldown_until: datetime | None = None
    wait_windows: int = 0


class SageRouter:
    def __init__(
        self,
        dwell_seconds: float,
        cooldown_seconds: float,
        stale_frame_seconds: float,
        learned_gate: LearnedGate | None = None,
        scalar_gate: ScalarUtilityGate | None = None,
    ):
        self.dwell = timedelta(seconds=dwell_seconds)
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.stale = timedelta(seconds=stale_frame_seconds)
        self.feeds: dict[str, FeedRuntime] = {}
        self.token_owner: str | None = None
        self.receipts: list[DecisionReceipt] = []
        self.total_receipts = 0
        self.total_deep_calls = 0
        self.learned_gate = learned_gate
        self.use_learned_gate = learned_gate is not None
        self.scalar_gate = scalar_gate
        self.use_scalar_gate = scalar_gate is not None

    def _predict(self, features: FrameFeatures) -> GateResult:
        if self.use_scalar_gate and self.scalar_gate:
            return self.scalar_gate.predict(features)
        if self.use_learned_gate and self.learned_gate:
            return self.learned_gate.predict(features)
        return self.gate(features)

    def _predict_legacy(self, features: FrameFeatures) -> GateResult:
        """Keep single-feed ingestion compatible; scalar routing requires a full window."""
        if self.use_learned_gate and self.learned_gate:
            return self.learned_gate.predict(features)
        return self.gate(features)

    @staticmethod
    def gate(features: FrameFeatures) -> GateResult:
        scores = {
            "crowd_geometry": min(
                1.0,
                0.55 * features.occupancy_ratio
                + 0.30 * min(features.person_count / 40, 1)
                + 0.15 * features.count_delta,
            ),
            "temporal_volatility": min(
                1.0, 0.60 * features.count_delta + 0.40 * features.confidence_variance
            ),
            "motion_change": min(1.0, 0.82 * features.motion_energy + 0.18 * features.count_delta),
            "recovery_value": min(
                1.0,
                0.45 * (1 - features.confidence_mean)
                + 0.30 * features.blur
                + 0.25 * features.blockiness,
            ),
        }
        selected = sorted(scores, key=scores.get, reverse=True)[:2]
        utility = min(
            1.0,
            0.5 * max(scores.values())
            + 0.2 * sorted(scores.values(), reverse=True)[1]
            + 0.15 * features.queue_depth / 10
            + 0.15 * (1 - features.confidence_mean),
        )
        return GateResult(scores=scores, selected=selected, utility=utility)

    def evaluate(self, features: FrameFeatures, policy: str = "sage") -> DecisionReceipt:
        started = perf_counter()
        now = datetime.now(UTC)
        runtime = self.feeds.setdefault(features.feed_id, FeedRuntime())
        previous = runtime.state
        gate = self._predict_legacy(features)
        runtime.latest, runtime.gate = features, gate
        stale = now - features.captured_at.astimezone(UTC) > self.stale
        can_claim = not stale and (runtime.cooldown_until is None or now >= runtime.cooldown_until)
        reason = "Observation retained: evidence below inspection threshold"
        executed = False

        if self.token_owner == features.feed_id:
            if (
                runtime.state_since
                and now - runtime.state_since >= self.dwell
                and gate.utility < 0.42
            ):
                runtime.state = FeedState.COOLDOWN
                runtime.cooldown_until = now + self.cooldown
                self.token_owner = None
                reason = "Dwell complete and utility fell below exit threshold"
            else:
                runtime.state = FeedState.DEEP_INSPECT
                executed = True
                reason = "Current token owner remains above exit threshold"
        elif self.token_owner is None and can_claim and gate.utility >= 0.56:
            runtime.state = FeedState.DEEP_INSPECT
            runtime.state_since = now
            self.token_owner = features.feed_id
            executed = True
            reason = "Utility crossed entry threshold; global token granted"
        elif stale:
            runtime.state = FeedState.OBSERVE
            reason = "Stale frame rejected before arbitration"
        elif runtime.cooldown_until and now < runtime.cooldown_until:
            runtime.state = FeedState.COOLDOWN
            reason = "Cooldown prevents immediate token reacquisition"
        elif gate.utility >= 0.48:
            runtime.state = FeedState.CANDIDATE
            reason = "Evidence is elevated; waiting for global token"
        else:
            runtime.state = FeedState.OBSERVE

        receipt = DecisionReceipt(
            receipt_id=f"R-{uuid4().hex[:8].upper()}",
            timestamp=now,
            feed_id=features.feed_id,
            previous_state=previous,
            next_state=runtime.state,
            policy=policy,
            shared_features=features,
            gate=gate,
            token_available=self.token_owner is None or self.token_owner == features.feed_id,
            deep_call_executed=executed,
            reason=reason,
            decision_latency_ms=(perf_counter() - started) * 1000,
        )
        self.receipts.insert(0, receipt)
        self.receipts = self.receipts[:200]
        self.total_receipts += 1
        self.total_deep_calls += int(executed)
        return receipt

    def rank_window(self, frames: list[FrameFeatures]) -> WindowRoutingDecision:
        """Rank one atomic decision window; the external scheduler executes the winner."""
        if not frames:
            raise ValueError("A routing window must contain at least one feed")
        feed_ids = [frame.feed_id for frame in frames]
        if len(set(feed_ids)) != len(feed_ids):
            raise ValueError("A routing window cannot contain duplicate feed IDs")

        now = datetime.now(UTC)
        candidates: list[tuple[FrameFeatures, GateResult, FeedRuntime]] = []
        for frame in frames:
            if now - frame.captured_at.astimezone(UTC) > self.stale:
                continue
            runtime = self.feeds.setdefault(frame.feed_id, FeedRuntime())
            gate = self._predict(frame)
            runtime.latest = frame
            runtime.gate = gate
            runtime.wait_windows += 1
            candidates.append((frame, gate, runtime))
        if not candidates:
            raise ValueError("A routing window has no non-stale feeds")

        ordered = sorted(
            candidates,
            key=lambda item: (-item[1].utility, -item[2].wait_windows, item[0].feed_id),
        )
        winner = ordered[0]
        winner[2].wait_windows = 0
        rankings = [
            RankedFeed(
                feed_id=frame.feed_id,
                predicted_proxy_utility=gate.utility,
                wait_windows=runtime.wait_windows,
                rank=index,
            )
            for index, (frame, gate, runtime) in enumerate(ordered, start=1)
        ]
        model = (
            self.scalar_gate.checkpoint_id
            if self.use_scalar_gate and self.scalar_gate
            else "fallback"
        )
        model_hash = (
            self.scalar_gate.checkpoint_sha256
            if self.use_scalar_gate and self.scalar_gate
            else None
        )
        return WindowRoutingDecision(
            timestamp=now,
            selected_feed_id=winner[0].feed_id,
            model=model,
            model_sha256=model_hash,
            rankings=rankings,
            reason=(
                "Highest predicted Tiny-over-Nano proxy utility; ties use longest wait, "
                "then lexicographic feed ID"
            ),
        )

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            generated_at=datetime.now(UTC),
            token_owner=self.token_owner,
            feeds=[
                FeedSnapshot(feed_id=k, state=v.state, gate=v.gate, latest=v.latest)
                for k, v in self.feeds.items()
            ],
            recent_receipts=self.receipts[:25],
        )

    def release_after_failure(self, feed_id: str) -> bool:
        if self.token_owner != feed_id:
            return False
        now = datetime.now(UTC)
        runtime = self.feeds[feed_id]
        runtime.state = FeedState.COOLDOWN
        runtime.state_since = now
        runtime.cooldown_until = now + self.cooldown
        self.token_owner = None
        return True
