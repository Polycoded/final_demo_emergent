from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .v2_schemas import ActiveOverride, CameraMode, CameraPolicy, ManualOverrideRequest


class CameraPolicyEngine:
    def __init__(self, policies: list[CameraPolicy] | None = None) -> None:
        self._policies = {item.camera_id: item for item in policies or []}
        self._overrides: dict[str, ActiveOverride] = {}
        self._lock = RLock()

    def list(self) -> list[CameraPolicy]:
        with self._lock:
            return sorted(self._policies.values(), key=lambda item: item.camera_id)

    def get(self, camera_id: str) -> CameraPolicy:
        with self._lock:
            if camera_id not in self._policies:
                raise KeyError(camera_id)
            return self._policies[camera_id]

    def upsert(self, policy: CameraPolicy) -> CameraPolicy:
        with self._lock:
            self._policies[policy.camera_id] = policy
            return policy

    def activate_override(
        self, camera_id: str, request: ManualOverrideRequest, now: datetime | None = None
    ) -> ActiveOverride:
        self.get(camera_id)
        created = now or datetime.now(UTC)
        expires = (
            created + timedelta(seconds=request.duration_seconds)
            if request.duration_seconds is not None
            else None
        )
        override = ActiveOverride(
            camera_id=camera_id,
            created_at=created,
            expires_at=expires,
            reason=request.reason,
        )
        with self._lock:
            self._overrides[camera_id] = override
        return override

    def release_override(self, camera_id: str) -> bool:
        with self._lock:
            return self._overrides.pop(camera_id, None) is not None

    def active_overrides(self, now: datetime | None = None) -> list[ActiveOverride]:
        current = now or datetime.now(UTC)
        with self._lock:
            expired = [
                camera_id
                for camera_id, item in self._overrides.items()
                if item.expires_at is not None and item.expires_at <= current
            ]
            for camera_id in expired:
                self._overrides.pop(camera_id, None)
            return sorted(self._overrides.values(), key=lambda item: item.camera_id)

    def has_override(self, camera_id: str, now: datetime | None = None) -> bool:
        return any(item.camera_id == camera_id for item in self.active_overrides(now))

    def effective_mode(self, policy: CameraPolicy, now: datetime | None = None) -> CameraMode:
        if policy.safety_requirement or policy.operating_mode == CameraMode.SAFETY:
            return CameraMode.SAFETY
        current = now or datetime.now(UTC)
        if not policy.schedule:
            return policy.operating_mode
        try:
            local = current.astimezone(ZoneInfo(policy.timezone))
        except ZoneInfoNotFoundError:
            return policy.operating_mode
        for rule in policy.schedule:
            if local.weekday() not in rule.days:
                continue
            start = time.fromisoformat(rule.start)
            end = time.fromisoformat(rule.end)
            active = start <= local.time() < end if start <= end else (
                local.time() >= start or local.time() < end
            )
            if active:
                return rule.mode
        return policy.operating_mode
