from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any

from .v2_schemas import CameraMode, CameraPolicy, CapacityReport, ModelSpec


class ResidentModelPool:
    """Registry and admission layer. Inference backends attach to these resident services."""

    def __init__(self, specs: list[ModelSpec] | None = None) -> None:
        self._models = {item.model_id: item for item in specs or []}
        self._instances: dict[str, Any] = {}
        self._lock = RLock()

    def register(self, spec: ModelSpec) -> ModelSpec:
        with self._lock:
            current = self._models.get(spec.model_id)
            if current and current.resident:
                spec.resident = True
                spec.warmed = current.warmed
                spec.load_events = current.load_events
            self._models[spec.model_id] = spec
            return spec

    def mark_resident(self, model_id: str, warmed: bool = True) -> ModelSpec:
        with self._lock:
            spec = self._models[model_id]
            if not spec.resident:
                spec.load_events += 1
            spec.resident = True
            spec.warmed = warmed
            return spec

    def load(self, model_id: str, loader: Callable[[], Any]) -> ModelSpec:
        """Load a service once; repeated calls reuse the existing resident instance."""
        with self._lock:
            if model_id in self._instances:
                return self._models[model_id]
            instance = loader()
            self._instances[model_id] = instance
            spec = self._models[model_id]
            spec.load_events += 1
            spec.resident = True
            spec.warmed = True
            provider = getattr(instance, "provider", None)
            if provider:
                spec.execution_provider = str(provider)
            return spec

    def instance(self, model_id: str) -> Any:
        with self._lock:
            if model_id not in self._instances:
                raise KeyError(f"Model {model_id} is not resident")
            return self._instances[model_id]

    def list(self) -> list[ModelSpec]:
        with self._lock:
            return sorted(self._models.values(), key=lambda item: item.model_id)

    def get(self, model_id: str) -> ModelSpec:
        with self._lock:
            if model_id not in self._models:
                raise KeyError(model_id)
            return self._models[model_id]

    def capacity(self, policies: list[CameraPolicy]) -> CapacityReport:
        required: dict[str, float] = {}
        for policy in policies:
            if policy.enabled and (
                policy.safety_requirement or policy.operating_mode == CameraMode.SAFETY
            ):
                required[policy.model_id] = (
                    required.get(policy.model_id, 0) + policy.minimum_deep_rate_fps
                )
        available = {item.model_id: item.safe_throughput_fps for item in self.list()}
        violations = []
        for model_id, demand in required.items():
            if model_id not in self._models:
                violations.append(f"{model_id}: no registered resident service")
            elif demand > self._models[model_id].safe_throughput_fps:
                violations.append(
                    f"{model_id}: protected demand {demand:.2f} FPS exceeds "
                    f"profiled safe throughput {self._models[model_id].safe_throughput_fps:.2f} FPS"
                )
        return CapacityReport(
            accepted=not violations,
            protected_required_fps=required,
            model_safe_fps=available,
            violations=violations,
        )
