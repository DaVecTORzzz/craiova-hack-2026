import importlib.util
from contextlib import contextmanager
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "demo_event", Path(__file__).resolve().parent.parent / "scripts" / "demo_event.py"
)
demo_event = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo_event)


def _use_test_client(monkeypatch, client) -> None:
    @contextmanager
    def fake_client(**kwargs):
        yield client  # keep the TestClient (and its lifespan) open

    monkeypatch.setattr(demo_event.httpx, "Client", fake_client)


def test_demo_event_restricted_zone(client, monkeypatch, capsys):
    _use_test_client(monkeypatch, client)

    assert demo_event.main(["--edge-token", "test-token"]) == 0

    event_id = capsys.readouterr().out.split()[2]
    data = client.get(f"/events/{event_id}").json()
    assert data["type"] == "RESTRICTED_ZONE"
    assert data["zone_id"] == "engine-left"
    assert data["context"] == {"engine_on": True}
    assert data["snapshot_url"] == f"/snapshots/{event_id}.jpg"
    assert client.get(data["snapshot_url"]).headers["content-type"] == "image/jpeg"

    stand12 = [c for c in client.get("/cameras").json() if c["id"] == "stand12"][0]
    assert stand12["engine_on"] is True


def test_demo_event_no_ppe_does_not_enable_engine(client, monkeypatch, capsys):
    _use_test_client(monkeypatch, client)

    assert demo_event.main(["--edge-token", "test-token", "--type", "NO_PPE"]) == 0

    event_id = capsys.readouterr().out.split()[2]
    data = client.get(f"/events/{event_id}").json()
    assert data["type"] == "NO_PPE"
    assert data["context"] == {"engine_on": False}

    stand12 = [c for c in client.get("/cameras").json() if c["id"] == "stand12"][0]
    assert stand12["engine_on"] is False


def test_demo_event_wrong_token_fails(client, monkeypatch):
    _use_test_client(monkeypatch, client)
    try:
        demo_event.main(["--edge-token", "wrong"])
    except demo_event.httpx.HTTPStatusError as e:
        assert e.response.status_code == 401
    else:
        raise AssertionError("expected 401")
