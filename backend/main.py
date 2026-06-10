"""
backend/main.py
---------------
FastAPI application entry point for Helix.

Exposes:
  POST /webhook/github  — receives GitHub Actions failure webhooks
  WS   /ws              — WebSocket endpoint for real-time dashboard updates
  GET  /health          — health check
  GET  /runs            — all stored Helix runs
  GET  /runs/{run_id}   — single run by ID

CORS is enabled for the Vite dev server (localhost:5173).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import FailureContext, HelixRun, RunStatus, WebhookPayload
from orchestrator import run_helix
import store

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Helix backend starting up…")
    yield
    logger.info("Helix backend shutting down.")


app = FastAPI(
    title="Helix CI/CD Agent",
    description="Autonomous self-healing CI/CD pipeline agent.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Vite dev server and any configured frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

def _verify_github_signature(body: bytes, signature_header: str | None) -> bool:
    """Return True if the HMAC-SHA256 signature matches the webhook secret."""
    if not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health():
    """Health check — returns status and active run count."""
    return {"status": "ok", "active_runs": store.run_count()}


@app.get("/runs", tags=["runs"])
async def list_runs():
    """Return all Helix runs, sorted newest first."""
    return [r.model_dump() for r in store.get_all_runs()]


@app.get("/runs/{run_id}", tags=["runs"])
async def get_run(run_id: str):
    """Return a single Helix run by ID."""
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run.model_dump()


@app.post("/webhook/github", tags=["webhook"])
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive a GitHub Actions workflow_run webhook.
    Verifies the HMAC signature, creates a HelixRun, and triggers the orchestrator.
    """
    body = await request.body()
    
    # Handle ping event first (no signature check needed)
    event_type = request.headers.get("X-Github-Event")
    if event_type == "ping":
        logger.info("Received GitHub ping — webhook connected successfully")
        return {"message": "pong"}

    # Verify signature for all other events
    sig = request.headers.get("X-Hub-Signature-256")
    if not _verify_github_signature(body, sig):
        logger.warning("Webhook signature verification failed — rejecting request")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Ignore non workflow_run events
    if event_type != "workflow_run":
        logger.info("Ignoring event type: %s", event_type)
        return {"message": f"Ignoring {event_type}"}

    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as exc:
        logger.error("Could not parse webhook payload: %s", exc)
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc
    # Only act on completed, failed workflow runs
    if payload.action != "completed":
        logger.info("Webhook ignored: action=%s", payload.action)
        return {"status": "ignored", "reason": "action is not 'completed'"}

    workflow_run = payload.workflow_run
    conclusion = workflow_run.get("conclusion", "")
    if conclusion not in ("failure", "action_required"):
        logger.info("Webhook ignored: conclusion=%s", conclusion)
        return {"status": "ignored", "reason": f"conclusion='{conclusion}' is not a failure"}

    # Build failure context from payload
    repo = payload.repository.get("full_name", "unknown/unknown")
    branch = workflow_run.get("head_branch", "main")
    commit_sha = workflow_run.get("head_sha", "")
    gh_run_id = str(workflow_run.get("id", ""))
    workflow_name = workflow_run.get("name", "unknown")

    # Extract failed job names
    failed_jobs: list[str] = []
    for job in workflow_run.get("pull_requests", []):
        failed_jobs.append(str(job))

    failure_context = FailureContext(
        repo=repo,
        branch=branch,
        commit_sha=commit_sha,
        run_id=gh_run_id,
        workflow_name=workflow_name,
        failed_jobs=failed_jobs,
    )

    helix_run = HelixRun(
        status=RunStatus.WATCHING,
        failure_context=failure_context,
    )
    store.save_run(helix_run)
    logger.info(
        "Created Helix run %s for %s @ %s (gh run %s)",
        helix_run.run_id, repo, commit_sha[:8], gh_run_id,
    )

    # Push to dashboard immediately — don't wait for orchestrator
    await store.broadcast("run_created", helix_run.model_dump())

    # Kick off orchestrator as a background task
    background_tasks.add_task(_run_orchestrator, helix_run)

    return {"status": "accepted", "run_id": helix_run.run_id}


async def _run_orchestrator(run: HelixRun) -> None:
    """Wrapper that runs the async Helix orchestrator inside a background task."""
    try:
        await run_helix(run)
    except Exception as exc:
        logger.exception("Orchestrator background task failed for run %s: %s", run.run_id, exc)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for the real-time Helix dashboard.
    On connect: sends full current state.
    Stays open: relays pings, handles disconnects gracefully.
    """
    await websocket.accept()
    store.register_connection(websocket)
    logger.info("New WebSocket client connected")

    try:
        # Send full current state to newly connected client
        await store.send_full_state(websocket)

        # Keep alive — handle incoming pings / close
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong"}')

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        store.unregister_connection(websocket)


# ---------------------------------------------------------------------------
# Dev server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
