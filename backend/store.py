"""
backend/store.py
----------------
In-memory run store and WebSocket broadcaster.
Holds all active HelixRun objects and the list of connected WebSocket clients.
Provides broadcast() to push JSON events to every connected client in real time.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from models import HelixRun

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------

# run_id -> HelixRun
_runs: dict[str, HelixRun] = {}

# Active WebSocket connections
_connections: list[WebSocket] = []


# ---------------------------------------------------------------------------
# Run store operations
# ---------------------------------------------------------------------------

def save_run(run: HelixRun) -> None:
    """Upsert a HelixRun in the store."""
    _runs[run.run_id] = run


def get_run(run_id: str) -> HelixRun | None:
    """Return a single run by ID, or None if not found."""
    return _runs.get(run_id)


def get_all_runs() -> list[HelixRun]:
    """Return all runs sorted by started_at descending (newest first)."""
    return sorted(_runs.values(), key=lambda r: r.started_at, reverse=True)


def run_count() -> int:
    """Return the number of stored runs."""
    return len(_runs)


# ---------------------------------------------------------------------------
# WebSocket connection registry
# ---------------------------------------------------------------------------

def register_connection(ws: WebSocket) -> None:
    """Add a newly accepted WebSocket connection to the registry."""
    _connections.append(ws)
    logger.info("WebSocket connected. Total connections: %d", len(_connections))


def unregister_connection(ws: WebSocket) -> None:
    """Remove a WebSocket connection from the registry."""
    if ws in _connections:
        _connections.remove(ws)
    logger.info("WebSocket disconnected. Total connections: %d", len(_connections))


# ---------------------------------------------------------------------------
# Broadcasting
# ---------------------------------------------------------------------------

def _serialize(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return _serialize(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    return obj


async def broadcast(event_type: str, data: Any) -> None:
    """
    Send a JSON event to every active WebSocket client.
    Silently drops dead connections.

    Event envelope: {"event": "<event_type>", "data": <data>}

    Supported event types:
      - run_created
      - trace_update
      - diagnosis_ready
      - fix_ready
      - sandbox_result
      - run_complete
    """
    payload = json.dumps({"event": event_type, "data": _serialize(data)})
    dead: list[WebSocket] = []

    for ws in list(_connections):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)

    for ws in dead:
        unregister_connection(ws)

    logger.debug("Broadcast '%s' to %d client(s)", event_type, len(_connections) - len(dead))


async def send_full_state(ws: WebSocket) -> None:
    """Send the complete current runs state to a newly connected client."""
    all_runs = [r.model_dump() for r in get_all_runs()]
    payload = json.dumps({
        "event": "full_state",
        "data": _serialize(all_runs),
    })
    await ws.send_text(payload)
