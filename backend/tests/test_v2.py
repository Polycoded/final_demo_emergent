from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.camera_policy import CameraPolicyEngine
from app.main import app
from app.model_pool import ResidentModelPool
from app.v2_scheduler import V2Scheduler
from app.v2_schemas import (
    CameraMode,
    CameraPolicy,
    ManualOverrideRequest,
    ModelSpec,
    ObserverSignals,
    TaskId,
)


def policy(camera_id: str, mode: CameraMode, priority: int = 3) -> CameraPolicy:
    return CameraPolicy(
        camera_id=camera_id,
        camera_name=camera_id,
        task_id=TaskId.PERSON,
        model_id="person-model",
        operating_mode=mode,
        priority=priority,
        minimum_deep_rate_fps=1 if mode == CameraMode.SAFETY else 0,
    )


def observation(camera_id: str, wait_ms: float = 100) -> ObserverSignals:
    return ObserverSignals(
        camera_id=camera_id,
        task_id=TaskId.PERSON,
        captured_at=datetime.now(UTC),
        motion=0.2,
        frame_difference=0.1,
        blur=0.1,
        brightness=0.5,
        contrast=0.5,
        entropy=0.5,
        time_since_deep_ms=wait_ms,
    )


def resident_pool(safe_fps: float = 20) -> ResidentModelPool:
    return ResidentModelPool(
        [
            ModelSpec(
                model_id="person-model",
                task_id=TaskId.PERSON,
                path="person.onnx",
                safe_throughput_fps=safe_fps,
                resident=True,
                warmed=True,
            )
        ]
    )


def test_safety_policy_always_beats_higher_adaptive_utility():
    policies = CameraPolicyEngine(
        [policy("SAFE", CameraMode.SAFETY, 5), policy("ADAPT", CameraMode.ADAPTIVE, 5)]
    )
    scheduler = V2Scheduler(policies, resident_pool())
    decision = scheduler.schedule(
        [observation("SAFE", 1100), observation("ADAPT", 100_000)]
    )
    assert decision.selected_camera_id == "SAFE"
    assert decision.decision_class == "PROTECTED"
    assert decision.reason_code == "SAFETY_REQUIREMENT"


def test_safety_camera_yields_after_its_minimum_rate_is_satisfied():
    policies = CameraPolicyEngine(
        [policy("SAFE", CameraMode.SAFETY, 5), policy("ADAPT", CameraMode.ADAPTIVE, 3)]
    )
    scheduler = V2Scheduler(policies, resident_pool())
    decision = scheduler.schedule([observation("SAFE", 100), observation("ADAPT", 100)])
    assert decision.selected_camera_id == "ADAPT"
    safe = next(item for item in decision.candidates if item.camera_id == "SAFE")
    assert not safe.eligible
    assert safe.reason_code == "PROTECTED_RATE_SATISFIED"


def test_manual_override_enters_protected_path_and_expires():
    now = datetime.now(UTC)
    policies = CameraPolicyEngine([policy("A", CameraMode.ADAPTIVE)])
    policies.activate_override(
        "A", ManualOverrideRequest(duration_seconds=5, reason="review test"), now
    )
    assert policies.has_override("A", now + timedelta(seconds=4))
    assert not policies.has_override("A", now + timedelta(seconds=6))


def test_capacity_rejects_protected_demand_above_profile():
    policies = [policy("A", CameraMode.SAFETY), policy("B", CameraMode.SAFETY)]
    report = resident_pool(safe_fps=1.5).capacity(policies)
    assert not report.accepted
    assert "exceeds" in report.violations[0]


def test_adaptive_dwell_prevents_one_second_camera_flicker():
    policies = CameraPolicyEngine(
        [policy("A", CameraMode.ADAPTIVE), policy("B", CameraMode.ADAPTIVE)]
    )
    scheduler = V2Scheduler(policies, resident_pool(), minimum_adaptive_dwell_seconds=4)
    now = datetime.now(UTC)
    first_a = observation("A").model_copy(update={"motion": 1.0, "frame_difference": 1.0})
    first_b = observation("B").model_copy(update={"motion": 0.0, "frame_difference": 0.0})
    assert scheduler.schedule([first_a, first_b], now).selected_camera_id == "A"
    second_a = observation("A").model_copy(update={"motion": 0.0, "frame_difference": 0.0})
    second_b = observation("B").model_copy(update={"motion": 1.0, "frame_difference": 1.0})
    held = scheduler.schedule([second_a, second_b], now + timedelta(seconds=1))
    assert held.selected_camera_id == "A"
    assert held.reason_code == "ADAPTIVE_DWELL_HOLD"
    switched = scheduler.schedule([second_a, second_b], now + timedelta(seconds=5))
    assert switched.selected_camera_id == "B"


def test_v2_api_exposes_policies_runtime_override_and_schedule():
    client = TestClient(app)
    cameras = client.get("/v2/cameras")
    assert cameras.status_code == 200
    assert {item["camera_id"] for item in cameras.json()} == {"A", "B", "C"}
    override = client.post(
        "/v2/cameras/C/override",
        json={"duration_seconds": 30, "reason": "operator review"},
    )
    assert override.status_code == 200
    payload = [
        {
            "camera_id": camera_id,
            "task_id": "PERSON",
            "captured_at": datetime.now(UTC).isoformat(),
            "motion": 0.2,
            "frame_difference": 0.1,
            "blur": 0.1,
            "brightness": 0.5,
            "contrast": 0.5,
            "entropy": 0.5,
            "time_since_deep_ms": 100,
        }
        for camera_id in ("A", "B", "C")
    ]
    scheduled = client.post("/v2/schedule", json=payload)
    assert scheduled.status_code == 200
    assert scheduled.json()["selected_camera_id"] in {"A", "C"}
    runtime = client.get("/v2/runtime")
    assert runtime.status_code == 200
    assert runtime.json()["capacity"]["accepted"] is True
    assert any(item["camera_id"] == "C" for item in runtime.json()["overrides"])
    assert client.delete("/v2/cameras/C/override").json()["released"] is True
