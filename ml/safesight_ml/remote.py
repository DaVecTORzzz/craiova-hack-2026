"""Fetch zones and engine state from the backend edge config endpoint."""

from __future__ import annotations

import httpx

from .zones import EdgeConfig


def fetch_edge_config(
    api_url: str,
    edge_token: str,
    camera_id: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 3.0,
) -> EdgeConfig:
    own_client = client is None
    client = client or httpx.Client(timeout=timeout)
    try:
        response = client.get(
            f"{api_url.rstrip('/')}/edge/zones",
            params={"camera_id": camera_id},
            headers={"X-Edge-Token": edge_token},
        )
        response.raise_for_status()
        return EdgeConfig.model_validate(response.json())
    finally:
        if own_client:
            client.close()
