import asyncio
from datetime import UTC, datetime

import pytest

from app.coordinator import WindowCoordinator
from app.router import SageRouter
from app.scalar_router import ScalarUtilityGate
from app.schemas import FrameFeatures
from app.store import ReceiptStore


class CountModel:
    def predict(self, values):
        return [row[0] for row in values]


def feature(feed_id: str, people: int) -> FrameFeatures:
    return FrameFeatures(
        feed_id=feed_id,
        captured_at=datetime.now(UTC),
        person_count=people,
        confidence_mean=0.7,
        confidence_variance=0.1,
        occupancy_ratio=0.2,
        count_delta=1,
        motion_energy=0.2,
        blur=0.1,
        blockiness=0.1,
        frame_age_ms=10,
        queue_depth=0,
        accelerator_utilization=0.1,
        expert_load=0.0,
    )


def test_coordinator_allocates_exactly_one_lease_and_persists_completion(tmp_path):
    async def scenario():
        published = []

        async def publish(payload):
            published.append(payload)

        store = ReceiptStore(tmp_path / "coordinator.db")
        scalar = ScalarUtilityGate(CountModel(), "count-model", "hash")
        router = SageRouter(5, 4, 2, scalar_gate=scalar)
        coordinator = WindowCoordinator(router, store, publish, expected_feeds=2)
        low, high = await asyncio.gather(
            coordinator.submit(feature("low", 2)),
            coordinator.submit(feature("high", 30)),
        )
        assert sum((low.selected, high.selected)) == 1
        selected = high if high.selected else low
        assert selected.selected_feed_id == "high"
        assert coordinator.status()["active_feed_id"] == "high"

        completed = await coordinator.complete("high", selected.call_id, 24.5)
        assert completed["execution"]["status"] == "completed"
        assert coordinator.status()["active_call_id"] is None
        assert store.list_recent_windows()[0]["execution"]["inference_ms"] == 24.5
        assert published

    asyncio.run(scenario())


def test_coordinator_rejects_a_mismatched_completion(tmp_path):
    async def scenario():
        async def publish(_payload):
            return None

        store = ReceiptStore(tmp_path / "coordinator.db")
        scalar = ScalarUtilityGate(CountModel(), "count-model", "hash")
        coordinator = WindowCoordinator(
            SageRouter(5, 4, 2, scalar_gate=scalar), store, publish, expected_feeds=1
        )
        result = await coordinator.submit(feature("A", 10))
        with pytest.raises(ValueError, match="does not match"):
            await coordinator.complete("A", "wrong-call", 1.0)
        await coordinator.complete("A", result.call_id, 1.0)

    asyncio.run(scenario())


def test_coordinator_timeout_releases_the_exclusive_lease(tmp_path):
    async def scenario():
        async def publish(_payload):
            return None

        store = ReceiptStore(tmp_path / "coordinator.db")
        scalar = ScalarUtilityGate(CountModel(), "count-model", "hash")
        coordinator = WindowCoordinator(
            SageRouter(5, 4, 2, scalar_gate=scalar),
            store,
            publish,
            expected_feeds=1,
            deep_timeout_seconds=0.05,
        )
        await coordinator.submit(feature("A", 10))
        await asyncio.sleep(0.15)
        assert coordinator.status()["active_call_id"] is None
        assert store.list_recent_windows()[0]["execution"]["status"] == "timeout"

    asyncio.run(scenario())
