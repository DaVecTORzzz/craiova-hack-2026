from tests.conftest import edge_event

HEADERS = {"X-Edge-Token": "test-token"}


def test_b05_websocket_broadcast(client):
    # Open 3 WebSocket clients
    with client.websocket_connect("/ws/events") as ws1, \
         client.websocket_connect("/ws/events") as ws2, \
         client.websocket_connect("/ws/events") as ws3:

        # 1. Post one event
        payload1 = edge_event()
        ev_id1 = payload1["event_id"]
        res1 = client.post("/edge/events", json=payload1, headers=HEADERS)
        assert res1.status_code == 201

        # Each client receives {"type": "event.created", "data": {...}} with right event_id
        for ws in (ws1, ws2, ws3):
            msg = ws.receive_json()
            assert msg["type"] == "event.created"
            assert msg["data"]["event_id"] == ev_id1
            assert msg["data"]["status"] == "open"
            assert msg["data"]["camera_id"] == payload1["camera_id"]
            assert msg["data"]["zone_id"] == payload1["zone_id"]

        # 2. Duplicate post sends nothing new
        res_dup = client.post("/edge/events", json=payload1, headers=HEADERS)
        assert res_dup.status_code == 200

        # 3. Post a second event
        payload2 = edge_event()
        ev_id2 = payload2["event_id"]
        res2 = client.post("/edge/events", json=payload2, headers=HEADERS)
        assert res2.status_code == 201

        # Check that the next message on each websocket is the second event, NOT a duplicate
        for ws in (ws1, ws2, ws3):
            msg = ws.receive_json()
            assert msg["type"] == "event.created"
            assert msg["data"]["event_id"] == ev_id2
