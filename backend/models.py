"""
backend/models.py
-----------------
Pydantic data models for the Helix CI/CD agent system.
Defines all domain objects: webhook payloads, agent findings,
diagnoses, fixes, trace steps, and the top-level HelixRun.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FailureType(str, enum.Enum):
    BUILD_ERROR = "BUILD_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    DEPENDENCY_CONFLICT = "DEPENDENCY_CONFLICT"
    ENV_ISSUE = "ENV_ISSUE"
    FLAKY_TEST = "FLAKY_TEST"
    UNKNOWN = "UNKNOWN"


class RunStatus(str, enum.Enum):
    WATCHING = "watching"
    DIAGNOSING = "diagnosing"
    FIXING = "fixing"
    VALIDATING = "validating"
    FIXED = "fixed"
    ESCALATED = "escalated"


class TraceStatus(str, enum.Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

class WebhookPayload(BaseModel):
    """Raw GitHub Actions workflow_run webhook payload (simplified)."""
    action: str
    workflow_run: dict[str, Any]
    repository: dict[str, Any]
    sender: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

class FailureContext(BaseModel):
    """All contextual information gathered about a CI failure."""
    repo: str                               # e.g. "org/repo"
    branch: str
    commit_sha: str
    run_id: str                             # GitHub Actions run ID
    workflow_name: str
    failed_jobs: list[str] = Field(default_factory=list)
    logs: str = ""                          # Raw CI log text
    diff: str = ""                          # Unified diff of failing commit
    dependencies: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent output
# ---------------------------------------------------------------------------

class AgentFinding(BaseModel):
    """A structured finding produced by one specialist agent."""
    agent_name: str
    finding_type: str                       # "log_analysis" | "diff_analysis" | "dependency_analysis"
    details: str                            # Human-readable explanation
    confidence: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

class Diagnosis(BaseModel):
    """Synthesised root-cause diagnosis produced by the supervisor."""
    failure_type: FailureType = FailureType.UNKNOWN
    root_cause: str
    affected_files: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    findings: list[AgentFinding] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Fix
# ---------------------------------------------------------------------------

class Fix(BaseModel):
    """A proposed code fix in unified diff format."""
    patch: str                              # Unified diff  --- a/... +++ b/...
    explanation: str
    files_changed: list[str] = Field(default_factory=list)
    test_commands: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Trace
# ---------------------------------------------------------------------------

class TraceStep(BaseModel):
    """A single step in the LangGraph execution timeline."""
    node_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    status: TraceStatus = TraceStatus.RUNNING


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------

class HelixRun(BaseModel):
    """Complete state object for one Helix execution run."""
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: RunStatus = RunStatus.WATCHING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    failure_context: Optional[FailureContext] = None
    diagnosis: Optional[Diagnosis] = None
    fix: Optional[Fix] = None
    sandbox_output: Optional[dict[str, Any]] = None   # {success, output, exit_code}
    pr_url: Optional[str] = None
    attempts: int = 0
    trace: list[TraceStep] = Field(default_factory=list)

    class Config:
        use_enum_values = True
