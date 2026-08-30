"""Equal-budget policy implementations used by replay benchmarks."""

from collections import defaultdict

from .gate import LearnedGate
from .router import SageRouter
from .scalar_router import ScalarUtilityGate
from .schemas import FrameFeatures


class PolicyArena:
    def __init__(
        self,
        learned_gate: LearnedGate | None = None,
        scalar_gate: ScalarUtilityGate | None = None,
    ) -> None:
        self.round_robin_index = 0
        self.calls: defaultdict[str, int] = defaultdict(int)
        self.learned_gate = learned_gate
        self.scalar_gate = scalar_gate

    def select(self, policy: str, frames: list[FrameFeatures], budget: int) -> list[FrameFeatures]:
        if policy == "always_light" or budget <= 0:
            return []
        ordered = sorted(frames, key=lambda item: item.feed_id)
        if policy == "round_robin":
            result = [
                ordered[(self.round_robin_index + offset) % len(ordered)]
                for offset in range(min(budget, len(ordered)))
            ]
            self.round_robin_index = (self.round_robin_index + budget) % len(ordered)
            return result
        if policy == "confidence_only":
            return sorted(frames, key=lambda item: item.confidence_mean)[:budget]
        if policy == "sage":
            score = (
                self.scalar_gate.predict
                if self.scalar_gate
                else self.learned_gate.predict
                if self.learned_gate
                else SageRouter.gate
            )
            return sorted(frames, key=lambda item: score(item).utility, reverse=True)[:budget]
        raise ValueError(f"Unknown policy: {policy}")
