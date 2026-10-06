from fastapi.testclient import TestClient

from backend.main import app


def test_api_end_to_end(shield, tmp_path, monkeypatch):
    app.state.shield = shield
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        clean = client.post("/api/v1/pipeline/run", json={"scenario": "clean"}).json()
        assert not clean["blocked"]
        attack = client.post("/api/v1/pipeline/run", json={"scenario": "attack", "session_id": "atk1"}).json()
        assert attack["blocked"]
        events = client.get("/api/v1/events", params={"min_tier": "FLAG"}).json()
        assert events and all(e["tier"] != "PASS" for e in events)
        assert client.get("/api/v1/sessions/atk1/trace").json()["events"]
        stats = client.get("/api/v1/stats").json()
        assert stats["total"] > 0 and stats["tiers"]["PASS"] > 0
        held = next(e for e in events if e["tier"] == "QUARANTINE")
        assert client.post(f"/api/v1/quarantine/{held['event_id']}/release").json()["status"] == "released"
        r = client.post("/api/v1/inspect", json={"session_id": "x", "role": "tool", "source": "w", "target": "f", "content": "ok"})
        assert r.json()["delivered"] is True
