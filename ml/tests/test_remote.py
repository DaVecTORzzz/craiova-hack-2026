from __future__ import annotations

import httpx

from safesight_ml.remote import fetch_edge_config

ZONE = {
    "id": "engine-left",
    "camera_id": "stand12",
    "name": "Motor stâng",
    "rule_type": "RESTRICTED",
    "active_when": "engine_on",
    "required_ppe": [],
    "severity": "CRITICAL",
    "debounce_s": 1.0,
    "escalate_after_s": 30,
    "notify_channel": "slack",
    "polygon": [[0.46, 0.16], [0.76, 0.16], [0.76, 0.68], [0.46, 0.68]],
    "reference_frame": None,
}


def test_fetch_edge_config_uses_token_and_camera():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/edge/zones"
        assert request.url.params["camera_id"] == "stand12"
        assert request.headers["X-Edge-Token"] == "test-token"
        return httpx.Response(
            200,
            json={
                "camera_id": "stand12",
                "engine_on": True,
                "config_version": 7,
                "zones": [ZONE],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    config = fetch_edge_config("http://backend/", "test-token", "stand12", client=client)

    assert config.engine_on is True
    assert config.config_version == 7
    assert config.zones[0].id == "engine-left"
