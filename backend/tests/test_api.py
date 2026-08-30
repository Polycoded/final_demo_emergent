import asyncio
from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient

from app.main import app


def test_health_and_ready_endpoints():
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    assert "cahma_token_budget_violations_total 0" in client.get("/metrics").text


def test_window_endpoint_returns_one_ranked_winner():
    client = TestClient(app)
    base = {
        "captured_at": datetime.now(UTC).isoformat(),
        "person_count": 10,
        "confidence_mean": 0.7,
        "confidence_variance": 0.1,
        "occupancy_ratio": 0.2,
        "count_delta": 1,
        "motion_energy": 0.2,
        "blur": 0.1,
        "blockiness": 0.1,
        "frame_age_ms": 20,
        "queue_depth": 0,
        "accelerator_utilization": 0.1,
        "expert_load": 0.1,
    }
    response = client.post(
        "/v1/features/window",
        json=[{"feed_id": "A", **base}, {"feed_id": "B", **base}],
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_feed_id"] in {"A", "B"}
    assert len(payload["rankings"]) == 2
    assert {item["rank"] for item in payload["rankings"]} == {1, 2}


def test_coordinated_api_issues_and_completes_one_deep_lease():
    async def scenario():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            base = {
                "captured_at": datetime.now(UTC).isoformat(),
                "person_count": 10,
                "confidence_mean": 0.7,
                "confidence_variance": 0.1,
                "occupancy_ratio": 0.2,
                "count_delta": 1,
                "motion_energy": 0.2,
                "blur": 0.1,
                "blockiness": 0.1,
                "frame_age_ms": 20,
                "queue_depth": 0,
                "accelerator_utilization": 0.1,
                "expert_load": 0.1,
            }
            responses = await asyncio.gather(
                *(
                    client.post(
                        "/v1/features/coordinated", json={"feed_id": feed_id, **base}
                    )
                    for feed_id in ("A", "B", "C")
                )
            )
            payloads = [response.json() for response in responses]
            assert all(response.status_code == 200 for response in responses)
            assert sum(payload["selected"] for payload in payloads) == 1
            selected = next(payload for payload in payloads if payload["selected"])
            completion = await client.post(
                f"/v1/deep/{selected['selected_feed_id']}/complete",
                json={"call_id": selected["call_id"], "inference_ms": 31.5},
            )
            assert completion.status_code == 200
            assert completion.json()["execution"]["status"] == "completed"

    asyncio.run(scenario())
