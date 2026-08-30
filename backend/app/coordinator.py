"""Async multi-camera batching with one exclusive heavyweight inference lease."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from .router import SageRouter
from .schemas import CoordinatedRoutingResponse, FrameFeatures
from .store import ReceiptStore


@dataclass
class PendingFeed:
    features: FrameFeatures
    future: asyncio.Future[CoordinatedRoutingResponse]


PublishWindow = Callable[[dict], Awaitable[None]]


class WindowCoordinator:
    def __init__(
        self,
        router: SageRouter,
        store: ReceiptStore,
        publish_window: PublishWindow,
        expected_feeds: int = 3,
        collect_ms: int = 250,
        deep_timeout_seconds: float = 4.0,
    ) -> None:
        self.router = router
        self.store = store
        self.publish_window = publish_window
        self.expected_feeds = max(1, expected_feeds)
        self.collect_seconds = max(0.01, collect_ms / 1000)
        self.deep_timeout_seconds = max(0.1, deep_timeout_seconds)
        self.pending: dict[str, PendingFeed] = {}
        self.active_call_id: str | None = None
        self.active_window_id: str | None = None
        self.active_feed_id: str | None = None
        self.lock = asyncio.Lock()
        self.collect_task: asyncio.Task | None = None
        self.timeout_task: asyncio.Task | None = None
        self.total_windows = 0
        self.completed_calls = 0
        self.failed_calls = 0
        self.timed_out_calls = 0

    async def submit(self, features: FrameFeatures) -> CoordinatedRoutingResponse:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[CoordinatedRoutingResponse] = loop.create_future()
        payload = None
        async with self.lock:
            existing = self.pending.get(features.feed_id)
            if existing and not existing.future.done():
                raise ValueError(f"Feed {features.feed_id} already has a pending window sample")
            self.pending[features.feed_id] = PendingFeed(features, future)
            if self.collect_task is None or self.collect_task.done():
                self.collect_task = asyncio.create_task(self._collect_deadline())
            if self.active_call_id is None and len(self.pending) >= self.expected_feeds:
                payload = self._finalize_locked()
        if payload:
            await self.publish_window(payload)
        return await future

    async def complete(
        self,
        feed_id: str,
        call_id: str,
        inference_ms: float,
        error: str | None = None,
    ) -> dict:
        publish_payload = None
        async with self.lock:
            if call_id != self.active_call_id or feed_id != self.active_feed_id:
                raise ValueError("Deep-call lease does not match the active allocation")
            status = "failed" if error else "completed"
            result = self._release_locked(status, inference_ms, error)
            if len(self.pending) >= self.expected_feeds:
                publish_payload = self._finalize_locked()
            elif self.pending and (self.collect_task is None or self.collect_task.done()):
                self.collect_task = asyncio.create_task(self._collect_deadline())
        await self.publish_window(result)
        if publish_payload:
            await self.publish_window(publish_payload)
        return result

    def status(self) -> dict:
        return {
            "active_call_id": self.active_call_id,
            "active_window_id": self.active_window_id,
            "active_feed_id": self.active_feed_id,
            "pending_feeds": sorted(self.pending),
            "total_windows": self.total_windows,
            "completed_calls": self.completed_calls,
            "failed_calls": self.failed_calls,
            "timed_out_calls": self.timed_out_calls,
        }

    async def _collect_deadline(self) -> None:
        await asyncio.sleep(self.collect_seconds)
        payload = None
        async with self.lock:
            self.collect_task = None
            if self.active_call_id is None and self.pending:
                payload = self._finalize_locked()
        if payload:
            await self.publish_window(payload)

    def _finalize_locked(self) -> dict:
        if self.active_call_id is not None or not self.pending:
            raise RuntimeError("Cannot allocate a second heavyweight call")
        submissions = list(self.pending.values())
        self.pending = {}
        if self.collect_task and not self.collect_task.done():
            self.collect_task.cancel()
        self.collect_task = None
        decision = self.router.rank_window([item.features for item in submissions])
        window_id = f"W-{uuid4().hex[:10].upper()}"
        call_id = f"D-{uuid4().hex[:10].upper()}"
        self.active_window_id = window_id
        self.active_call_id = call_id
        self.active_feed_id = decision.selected_feed_id
        self.total_windows += 1
        payload = {
            "window_id": window_id,
            "call_id": call_id,
            "created_at": decision.timestamp.isoformat(),
            "selected_feed_id": decision.selected_feed_id,
            "decision": decision.model_dump(mode="json"),
            "features": [item.features.model_dump(mode="json") for item in submissions],
            "execution": {"status": "allocated", "inference_ms": None, "error": None},
        }
        self.store.save_window(window_id, payload["created_at"], payload)
        for item in submissions:
            if not item.future.done():
                item.future.set_result(
                    CoordinatedRoutingResponse(
                        window_id=window_id,
                        call_id=call_id,
                        selected=item.features.feed_id == decision.selected_feed_id,
                        selected_feed_id=decision.selected_feed_id,
                        decision=decision,
                    )
                )
        self.timeout_task = asyncio.create_task(self._deep_deadline(call_id, window_id))
        return payload

    async def _deep_deadline(self, call_id: str, window_id: str) -> None:
        await asyncio.sleep(self.deep_timeout_seconds)
        publish_payload = None
        timeout_payload = None
        async with self.lock:
            if call_id != self.active_call_id or window_id != self.active_window_id:
                return
            timeout_payload = self._release_locked(
                "timeout", self.deep_timeout_seconds * 1000, "Deep inference lease expired"
            )
            if len(self.pending) >= self.expected_feeds:
                publish_payload = self._finalize_locked()
            elif self.pending and (self.collect_task is None or self.collect_task.done()):
                self.collect_task = asyncio.create_task(self._collect_deadline())
        if timeout_payload:
            await self.publish_window(timeout_payload)
        if publish_payload:
            await self.publish_window(publish_payload)

    def _release_locked(self, status: str, inference_ms: float, error: str | None) -> dict:
        window_id = self.active_window_id
        call_id = self.active_call_id
        feed_id = self.active_feed_id
        if not window_id or not call_id or not feed_id:
            raise RuntimeError("No active heavyweight call")
        if self.timeout_task and self.timeout_task is not asyncio.current_task():
            self.timeout_task.cancel()
        self.timeout_task = None
        execution = {
            "status": status,
            "completed_at": datetime.now(UTC).isoformat(),
            "inference_ms": inference_ms,
            "error": error,
        }
        payload = self.store.update_window_execution(window_id, execution) or {
            "window_id": window_id,
            "call_id": call_id,
            "selected_feed_id": feed_id,
            "execution": execution,
        }
        if status == "completed":
            self.completed_calls += 1
        elif status == "timeout":
            self.timed_out_calls += 1
        else:
            self.failed_calls += 1
        self.active_call_id = None
        self.active_window_id = None
        self.active_feed_id = None
        return payload
