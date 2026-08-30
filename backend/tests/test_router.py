from datetime import UTC, datetime, timedelta

import numpy as np

from app.benchmark import run_equal_budget_replay
from app.detectors import occupancy_union
from app.gate import LearnedGate
from app.router import SageRouter
from app.scalar_router import ScalarUtilityGate, transform
from app.schemas import FeedState, FrameFeatures
from app.vision import OpenCvFeatureExtractor


def feature(feed_id: str, **overrides):
    payload = {
        "feed_id": feed_id,
        "captured_at": datetime.now(UTC),
        "person_count": 12,
        "confidence_mean": 0.65,
        "confidence_variance": 0.2,
        "occupancy_ratio": 0.55,
        "count_delta": 0.4,
        "motion_energy": 0.95,
        "blur": 0.15,
        "blockiness": 0.1,
        "frame_age_ms": 30,
        "queue_depth": 1,
        "accelerator_utilization": None,
        "expert_load": 0.1,
    }
    payload.update(overrides)
    return FrameFeatures(**payload)


def test_router_grants_exactly_one_token():
    router = SageRouter(5, 4, 2)
    first = router.evaluate(feature("A"))
    second = router.evaluate(feature("B"))
    assert first.next_state == FeedState.DEEP_INSPECT
    assert first.deep_call_executed is True
    assert second.deep_call_executed is False
    assert router.token_owner == "A"


def test_router_rejects_stale_frame():
    router = SageRouter(5, 4, 0.001)
    stale = feature("A", captured_at=datetime.now(UTC) - timedelta(seconds=1))
    receipt = router.evaluate(stale)
    assert receipt.deep_call_executed is False
    assert "Stale" in receipt.reason


def test_feature_extractor_emits_normalized_edge_features():
    extractor = OpenCvFeatureExtractor("north")
    frame = np.zeros((96, 128, 3), dtype=np.uint8)
    first = extractor.analyze(frame)
    frame[:, 20:30] = 255
    second = extractor.analyze(frame)
    assert first.feed_id == "north"
    assert 0 <= second.motion_energy <= 1
    assert 0 <= second.blur <= 1
    assert 0 <= second.occupancy_ratio <= 1


def test_policy_arena_keeps_equal_budget():
    first, second = feature("A"), feature("B", confidence_mean=0.2)
    labels = {
        (first.feed_id, first.captured_at.isoformat()): 0.1,
        (second.feed_id, second.captured_at.isoformat()): 0.8,
    }
    results = run_equal_budget_replay([[first, second]], labels, budget=1)
    assert all(result.deep_calls <= 1 for result in results)
    assert next(item for item in results if item.policy == "sage").deep_calls == 1


def test_learned_gate_keeps_top_two_sparse_contract():
    result = LearnedGate.fallback().predict(feature("A"))
    assert len(result.selected) == 2
    assert set(result.selected).issubset(result.scores)
    assert all(0 <= score <= 1 for score in result.scores.values())


def test_deep_failure_releases_token_into_cooldown():
    router = SageRouter(5, 4, 2)
    router.evaluate(feature("A"))
    assert router.release_after_failure("A") is True
    assert router.token_owner is None
    assert router.feeds["A"].state == FeedState.COOLDOWN


class FakeScalarModel:
    def predict(self, values):
        return [row[0] for row in values]


def test_scalar_transform_matches_frozen_contract():
    values = transform(
        feature(
            "A",
            person_count=80,
            count_delta=20,
            frame_age_ms=1000,
            queue_depth=5,
            accelerator_utilization=0.25,
        )
    )
    assert values[0] == 1.0
    assert values[4] == 0.5
    assert values[8:12] == [0.5, 0.5, 0.25, 0.1]


def test_scalar_window_ranks_all_feeds_and_uses_one_winner():
    scalar = ScalarUtilityGate(FakeScalarModel(), "test-router", "abc123")
    router = SageRouter(5, 4, 2, scalar_gate=scalar)
    decision = router.rank_window(
        [
            feature("low", person_count=4, accelerator_utilization=0.0),
            feature("high", person_count=32, accelerator_utilization=0.0),
        ]
    )
    assert decision.selected_feed_id == "high"
    assert [item.feed_id for item in decision.rankings] == ["high", "low"]
    assert decision.model_sha256 == "abc123"


def test_scalar_window_tie_breaks_by_wait_then_feed_id():
    scalar = ScalarUtilityGate(FakeScalarModel(), "test-router", "abc123")
    router = SageRouter(5, 4, 2, scalar_gate=scalar)
    first = router.rank_window(
        [
            feature("B", person_count=8, accelerator_utilization=0.0),
            feature("A", person_count=8, accelerator_utilization=0.0),
        ]
    )
    second = router.rank_window(
        [
            feature("B", person_count=8, accelerator_utilization=0.0),
            feature("A", person_count=8, accelerator_utilization=0.0),
        ]
    )
    assert first.selected_feed_id == "A"
    assert second.selected_feed_id == "B"


def test_legacy_single_feed_path_accepts_missing_accelerator_telemetry():
    scalar = ScalarUtilityGate(FakeScalarModel(), "test-router", "abc123")
    router = SageRouter(5, 4, 2, scalar_gate=scalar)
    receipt = router.evaluate(feature("legacy", accelerator_utilization=None))
    assert receipt.gate.selected != ["tiny_over_nano"]


def test_occupancy_union_uses_original_pixel_boxes_without_double_counting():
    boxes = ((0.0, 0.0, 50.0, 100.0), (25.0, 0.0, 75.0, 100.0))
    assert occupancy_union(boxes, 100, 100) == 0.75


def test_occupancy_union_clamps_boxes_to_frame_bounds():
    assert occupancy_union(((-10.0, -20.0, 110.0, 120.0),), 100, 100) == 1.0
