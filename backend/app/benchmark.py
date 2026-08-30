"""Reproducible equal-budget policy replay. Teacher disagreement remains a proxy metric."""

from dataclasses import dataclass

from .gate import LearnedGate
from .policies import PolicyArena
from .schemas import FrameFeatures


@dataclass
class PolicyResult:
    policy: str
    deep_calls: int
    captured_disagreement: float
    allocation_regret: float


def run_equal_budget_replay(
    windows: list[list[FrameFeatures]],
    teacher_disagreement: dict[tuple[str, str], float],
    budget: int = 1,
    learned_gate: LearnedGate | None = None,
) -> list[PolicyResult]:
    results: list[PolicyResult] = []
    for policy in ("always_light", "round_robin", "confidence_only", "sage"):
        arena = PolicyArena(learned_gate)
        captured = 0.0
        ideal = 0.0
        calls = 0
        for window in windows:
            selected = arena.select(policy, window, budget)
            selected_ids = {item.feed_id for item in selected}
            captured += sum(
                teacher_disagreement.get((item.feed_id, item.captured_at.isoformat()), 0.0)
                for item in selected
            )
            ideal += sum(
                sorted(
                    (
                        teacher_disagreement.get((item.feed_id, item.captured_at.isoformat()), 0.0)
                        for item in window
                    ),
                    reverse=True,
                )[:budget]
            )
            calls += len(selected_ids)
        results.append(PolicyResult(policy, calls, captured, max(0.0, ideal - captured)))
    return results
