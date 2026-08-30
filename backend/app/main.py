import asyncio
import base64
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from secrets import compare_digest
from time import perf_counter

import cv2
import numpy as np
from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from .camera_policy import CameraPolicyEngine
from .config import origins, settings
from .coordinator import WindowCoordinator
from .detectors import YoloXOnnxDetector
from .gate import LearnedGate
from .model_pool import ResidentModelPool
from .router import SageRouter
from .scalar_router import ScalarUtilityGate
from .schemas import (
    CoordinatedRoutingResponse,
    DecisionReceipt,
    DeepExecutionReport,
    FrameFeatures,
    RuntimeSnapshot,
    WindowRoutingDecision,
)
from .store import ReceiptStore
from .telemetry import read_nvidia_gpu
from .v2_scheduler import V2Scheduler
from .v2_schemas import (
    CameraMode,
    CameraPolicy,
    ManualOverrideRequest,
    ModelSpec,
    ObserverSignals,
    ResidentInferenceRequest,
    TaskId,
    V2RuntimeSnapshot,
    V2SchedulingDecision,
)

learned_gate = (
    LearnedGate.load(settings.gate_checkpoint)
    if settings.gate_checkpoint and settings.gate_checkpoint.exists()
    else None
)
scalar_gate = (
    ScalarUtilityGate.load(settings.scalar_router_checkpoint, settings.scalar_router_sha256)
    if settings.scalar_router_checkpoint and settings.scalar_router_checkpoint.exists()
    else None
)
router = SageRouter(
    settings.deep_dwell_seconds,
    settings.cooldown_seconds,
    settings.stale_frame_seconds,
    learned_gate=learned_gate,
    scalar_gate=scalar_gate,
)
store = ReceiptStore(settings.database_path)
subscribers: set[WebSocket] = set()

policy_engine = CameraPolicyEngine(
    [
        CameraPolicy(
            camera_id="A",
            camera_name="North Concourse",
            location="Demo Zone A",
            task_id=TaskId.PERSON,
            model_id="person-yolox-tiny",
            operating_mode=CameraMode.SAFETY,
            priority=5,
            minimum_deep_rate_fps=0.2,
            maximum_deep_rate_fps=5,
        ),
        CameraPolicy(
            camera_id="B",
            camera_name="East Entry",
            location="Demo Zone B",
            task_id=TaskId.PERSON,
            model_id="person-yolox-tiny",
            operating_mode=CameraMode.PRIORITY,
            priority=4,
        ),
        CameraPolicy(
            camera_id="C",
            camera_name="Garden Gate",
            location="Demo Zone C",
            task_id=TaskId.PERSON,
            model_id="person-yolox-tiny",
            operating_mode=CameraMode.ADAPTIVE,
            priority=3,
        ),
    ]
)
model_pool = ResidentModelPool(
    [
        ModelSpec(
            model_id="person-yolox-tiny",
            task_id=TaskId.PERSON,
            path="models/yolox_tiny.onnx",
            execution_provider="ONNXRuntime",
            safe_throughput_fps=12,
        )
    ]
)
try:
    model_pool.load("person-yolox-tiny", lambda: YoloXOnnxDetector("models/yolox_tiny.onnx"))
except (OSError, ValueError):
    # Readiness and capacity APIs expose the unavailable state; v1 remains usable.
    pass
v2_scheduler = V2Scheduler(policy_engine, model_pool)


def require_key(x_cahma_key: str = Header(default="")) -> None:
    if settings.environment == "production" and settings.api_key == "change-me-before-deployment":
        raise HTTPException(status_code=503, detail="Production API key is not configured")
    if settings.api_key != "change-me-before-deployment" and not compare_digest(
        x_cahma_key, settings.api_key
    ):
        raise HTTPException(status_code=401, detail="Invalid CAHMA API key")


async def publish(receipt: DecisionReceipt) -> None:
    stale: list[WebSocket] = []
    payload = {"type": "decision", "data": receipt.model_dump(mode="json")}
    for socket in subscribers:
        try:
            await socket.send_json(payload)
        except RuntimeError:
            stale.append(socket)
    for socket in stale:
        subscribers.discard(socket)


async def publish_window(payload: dict) -> None:
    stale: list[WebSocket] = []
    message = {"type": "window_decision", "data": payload}
    for socket in subscribers:
        try:
            await socket.send_json(message)
        except RuntimeError:
            stale.append(socket)
    for socket in stale:
        subscribers.discard(socket)


async def publish_v2(payload: dict) -> None:
    stale: list[WebSocket] = []
    message = {"type": "v2_decision", "data": payload}
    for socket in subscribers:
        try:
            await socket.send_json(message)
        except RuntimeError:
            stale.append(socket)
    for socket in stale:
        subscribers.discard(socket)


coordinator = WindowCoordinator(
    router,
    store,
    publish_window,
    settings.coordinator_feed_count,
    settings.coordinator_collect_ms,
    settings.deep_timeout_seconds,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-CAHMA-Key", "X-Request-Id"],
)


@app.middleware("http")
async def security_and_timing(request: Request, call_next):
    started = perf_counter()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Process-Time-Ms"] = f"{(perf_counter() - started) * 1000:.2f}"
    return response


@app.get("/healthz")
async def health() -> dict:
    return {
        "status": "ok",
        "runtime_version": settings.runtime_version,
        "time": datetime.now(UTC).isoformat(),
        "token_owner": router.token_owner,
        "router_mode": "scalar" if router.use_scalar_gate else "fallback",
        "router_model_sha256": (
            router.scalar_gate.checkpoint_sha256 if router.scalar_gate else None
        ),
        "coordinator": coordinator.status(),
    }


@app.get("/readyz")
async def ready() -> JSONResponse:
    secure = (
        settings.environment != "production" or settings.api_key != "change-me-before-deployment"
    )
    return JSONResponse(
        status_code=200 if secure else 503,
        content={"ready": secure, "environment": settings.environment},
    )


@app.post("/v1/features", response_model=DecisionReceipt, dependencies=[Depends(require_key)])
async def ingest_features(features: FrameFeatures) -> DecisionReceipt:
    receipt = router.evaluate(features)
    store.save(receipt)
    await publish(receipt)
    return receipt


@app.post(
    "/v1/features/window",
    response_model=WindowRoutingDecision,
    dependencies=[Depends(require_key)],
)
async def rank_feature_window(features: list[FrameFeatures]) -> WindowRoutingDecision:
    try:
        return router.rank_window(features)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post(
    "/v1/features/coordinated",
    response_model=CoordinatedRoutingResponse,
    dependencies=[Depends(require_key)],
)
async def coordinate_feature(features: FrameFeatures) -> CoordinatedRoutingResponse:
    try:
        return await coordinator.submit(features)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/v1/runtime", response_model=RuntimeSnapshot, dependencies=[Depends(require_key)])
async def runtime() -> RuntimeSnapshot:
    return router.snapshot()


@app.get("/v1/receipts", dependencies=[Depends(require_key)])
async def receipts() -> list[dict]:
    return store.list_recent()


@app.get("/v1/windows", dependencies=[Depends(require_key)])
async def windows() -> list[dict]:
    return store.list_recent_windows()


@app.get("/v1/telemetry", dependencies=[Depends(require_key)])
async def telemetry() -> dict:
    return read_nvidia_gpu().__dict__


@app.get("/v2/cameras", response_model=list[CameraPolicy], dependencies=[Depends(require_key)])
async def list_v2_cameras() -> list[CameraPolicy]:
    return policy_engine.list()


@app.put(
    "/v2/cameras/{camera_id}",
    response_model=CameraPolicy,
    dependencies=[Depends(require_key)],
)
async def upsert_v2_camera(camera_id: str, policy: CameraPolicy) -> CameraPolicy:
    if camera_id != policy.camera_id:
        raise HTTPException(status_code=422, detail="Path and payload camera IDs must match")
    try:
        model_pool.get(policy.model_id)
    except KeyError as error:
        raise HTTPException(status_code=409, detail="Production model is not registered") from error
    return policy_engine.upsert(policy)


@app.post(
    "/v2/cameras/{camera_id}/override",
    dependencies=[Depends(require_key)],
)
async def activate_v2_override(camera_id: str, request: ManualOverrideRequest) -> dict:
    try:
        override = policy_engine.activate_override(camera_id, request)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Camera is not configured") from error
    payload = override.model_dump(mode="json")
    await publish_v2({"event": "override_activated", **payload})
    return payload


@app.delete(
    "/v2/cameras/{camera_id}/override",
    dependencies=[Depends(require_key)],
)
async def release_v2_override(camera_id: str) -> dict:
    released = policy_engine.release_override(camera_id)
    if released:
        await publish_v2({"event": "override_released", "camera_id": camera_id})
    return {"camera_id": camera_id, "released": released}


@app.post(
    "/v2/schedule",
    response_model=V2SchedulingDecision,
    dependencies=[Depends(require_key)],
)
async def schedule_v2(observations: list[ObserverSignals]) -> V2SchedulingDecision:
    capacity = model_pool.capacity(policy_engine.list())
    if not capacity.accepted:
        raise HTTPException(status_code=409, detail={"capacity": capacity.model_dump()})
    try:
        decision = v2_scheduler.schedule(observations)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    payload = decision.model_dump(mode="json")
    store.save_v2(decision.decision_id, decision.timestamp.isoformat(), payload)
    await publish_v2(payload)
    return decision


@app.get(
    "/v2/runtime",
    response_model=V2RuntimeSnapshot,
    dependencies=[Depends(require_key)],
)
async def runtime_v2() -> V2RuntimeSnapshot:
    return V2RuntimeSnapshot(
        generated_at=datetime.now(UTC),
        cameras=policy_engine.list(),
        overrides=policy_engine.active_overrides(),
        models=model_pool.list(),
        capacity=model_pool.capacity(policy_engine.list()),
        recent_decisions=v2_scheduler.recent_decisions(),
    )


@app.post("/v2/models/{model_id}/infer", dependencies=[Depends(require_key)])
async def infer_resident_model(model_id: str, request: ResidentInferenceRequest) -> dict:
    try:
        encoded = base64.b64decode(request.frame_base64, validate=True)
        frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Frame is not a decodable image")
        detector = model_pool.instance(model_id)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    result = await asyncio.to_thread(detector.detect, frame)
    payload = {
        "camera_id": request.camera_id,
        "decision_id": request.decision_id,
        "model_id": model_id,
        "provider": detector.provider,
        "person_count": result.count,
        "confidence_mean": result.confidence_mean,
        "boxes_xyxy": result.boxes_xyxy,
        "inference_ms": result.inference_ms,
    }
    await publish_v2({"event": "resident_inference", **payload})
    return payload


@app.get("/v2/receipts", dependencies=[Depends(require_key)])
async def receipts_v2() -> list[dict]:
    return store.list_recent_v2()


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> str:
    receipts = router.receipts
    latencies = sorted(receipt.decision_latency_ms for receipt in receipts)
    p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0
    return (
        "\n".join(
            [
                "# TYPE cahma_receipts_total counter",
                f"cahma_receipts_total {router.total_receipts}",
                "# TYPE cahma_deep_calls_total counter",
                f"cahma_deep_calls_total {router.total_deep_calls + coordinator.total_windows}",
                "# TYPE cahma_window_decisions_total counter",
                f"cahma_window_decisions_total {coordinator.total_windows}",
                "# TYPE cahma_deep_timeouts_total counter",
                f"cahma_deep_timeouts_total {coordinator.timed_out_calls}",
                "# TYPE cahma_deep_failures_total counter",
                f"cahma_deep_failures_total {coordinator.failed_calls}",
                "# TYPE cahma_token_budget_violations_total counter",
                "cahma_token_budget_violations_total 0",
                "# TYPE cahma_decision_latency_p95_ms gauge",
                f"cahma_decision_latency_p95_ms {p95:.3f}",
            ]
        )
        + "\n"
    )


@app.get("/v1/runs", dependencies=[Depends(require_key)])
async def formal_runs() -> list[dict]:
    settings.formal_runs_path.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for path in sorted(settings.formal_runs_path.glob("*.json"), reverse=True):
        try:
            artifacts.append({"name": path.name, **json.loads(path.read_text(encoding="utf-8"))})
        except (OSError, json.JSONDecodeError):
            continue
    return artifacts


@app.post("/v1/gate/{mode}", dependencies=[Depends(require_key)])
async def gate_mode(mode: str) -> dict:
    if mode not in {"scalar", "learned", "fallback"}:
        raise HTTPException(status_code=400, detail="Mode must be scalar, learned or fallback")
    if mode == "scalar" and router.scalar_gate is None:
        raise HTTPException(status_code=409, detail="No scalar router checkpoint is loaded")
    if mode == "learned" and router.learned_gate is None:
        raise HTTPException(status_code=409, detail="No learned gate checkpoint is loaded")
    router.use_scalar_gate = mode == "scalar"
    router.use_learned_gate = mode == "learned"
    return {"mode": mode}


@app.post("/v1/deep/{feed_id}/complete", dependencies=[Depends(require_key)])
async def deep_complete(feed_id: str, report: DeepExecutionReport) -> dict:
    try:
        return await coordinator.complete(feed_id, report.call_id, report.inference_ms)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/v1/deep/{feed_id}/failure", dependencies=[Depends(require_key)])
async def deep_failure(feed_id: str, report: DeepExecutionReport | None = None) -> dict:
    if report is not None:
        try:
            return await coordinator.complete(
                feed_id,
                report.call_id,
                report.inference_ms,
                report.error or "Deep inference failed",
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
    released = router.release_after_failure(feed_id)
    return {"feed_id": feed_id, "token_released": released}


@app.websocket("/v1/events")
async def events(socket: WebSocket) -> None:
    provided_key = socket.query_params.get("key", "")
    trusted_origin = socket.headers.get("origin", "") in origins()
    if (
        settings.environment == "production"
        and not trusted_origin
        and not compare_digest(provided_key, settings.api_key)
    ):
        await socket.close(code=1008)
        return
    await socket.accept()
    subscribers.add(socket)
    try:
        await socket.send_json(
            {"type": "snapshot", "data": router.snapshot().model_dump(mode="json")}
        )
        windows = store.list_recent_windows(1)
        if windows:
            await socket.send_json({"type": "window_decision", "data": windows[0]})
        await socket.send_json(
            {
                "type": "v2_snapshot",
                "data": (await runtime_v2()).model_dump(mode="json"),
            }
        )
        while True:
            await asyncio.sleep(30)
            await socket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        subscribers.discard(socket)
