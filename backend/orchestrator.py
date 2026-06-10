"""
backend/orchestrator.py
------------------------
Helix self-healing pipeline — plain asyncio implementation.

Executes 8 steps in sequence, broadcasting WebSocket events after each:
  1. assemble_context  — fetch logs, diff, deps in parallel
  2. triage            — decide which specialist agents to run
  3. run_specialists   — run relevant agents in parallel
  4. diagnose          — synthesise findings into a Diagnosis
  5. generate_fix      — produce a unified-diff Fix
  6. validate          — run fix in Docker sandbox
  7. open_pr           — open GitHub PR on success
  8. retry_or_escalate — retry or escalate on sandbox failure

No external graph library required — uses asyncio.gather for parallelism.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

import google.generativeai as genai

from agents.dep_agent import DependencyAgent
from agents.diff_agent import DiffAnalysisAgent
from agents.log_agent import LogAnalysisAgent
from config import settings
from models import (
    AgentFinding,
    Diagnosis,
    FailureType,
    Fix,
    HelixRun,
    RunStatus,
    TraceStatus,
    TraceStep,
)
from tools import github_tools
from tools.sandbox import run_in_sandbox
import store

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_trace(run: HelixRun, node_name: str, summary: str,
               status: TraceStatus = TraceStatus.DONE) -> None:
    """Append a TraceStep and persist to the store."""
    step = TraceStep(
        node_name=node_name,
        summary=summary,
        status=status,
        timestamp=datetime.utcnow(),
    )
    run.trace.append(step)
    store.save_run(run)


def _gemini_json(system: str, user: str) -> dict[str, Any]:
    """Call Gemini with system + user prompt and return parsed JSON dict."""
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system,
    )
    response = model.generate_content(user)
    raw = response.text.strip()
    
    # Strip markdown fences if present
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini JSON response: %s\nRaw: %s", e, raw[:500])
        raise


async def _broadcast_trace(run: HelixRun) -> None:
    await store.broadcast("trace_update", {
        "run_id": run.run_id,
        "trace": [t.model_dump() for t in run.trace],
    })


# ---------------------------------------------------------------------------
# Step 1: assemble_context
# ---------------------------------------------------------------------------

async def _assemble_context(run: HelixRun) -> None:
    ctx = run.failure_context
    if ctx is None:
        logger.error("assemble_context: no failure_context on run")
        return

    run.status = RunStatus.DIAGNOSING
    _add_trace(run, "assemble_context", "Gathering CI logs, diff, and dependencies…", TraceStatus.RUNNING)
    store.save_run(run)
    await _broadcast_trace(run)

    loop = asyncio.get_event_loop()
    logs_fut = loop.run_in_executor(None, github_tools.fetch_logs, ctx.repo, ctx.run_id)
    diff_fut  = loop.run_in_executor(None, github_tools.fetch_diff, ctx.repo, ctx.commit_sha)
    deps_fut  = loop.run_in_executor(None, github_tools.fetch_deps, ctx.repo, ctx.commit_sha)

    logs, diff, deps = await asyncio.gather(logs_fut, diff_fut, deps_fut, return_exceptions=True)

    ctx.logs         = logs if isinstance(logs, str) else f"[Error] {logs}"
    ctx.diff         = diff if isinstance(diff, str) else f"[Error] {diff}"
    ctx.dependencies = deps if isinstance(deps, dict) else {}

    _add_trace(run, "assemble_context", "Context assembled — logs, diff, deps fetched")
    await _broadcast_trace(run)


# ---------------------------------------------------------------------------
# Step 2: triage
# ---------------------------------------------------------------------------

async def _triage(run: HelixRun) -> list[str]:
    _add_trace(run, "triage", "Triaging failure type…", TraceStatus.RUNNING)
    ctx = run.failure_context

    system = (
        "You are the triage supervisor for Helix, an autonomous CI/CD agent. "
        "Decide which specialist agents to run. "
        "Return JSON: {\"agents\": [\"log\", \"diff\", \"dep\"]} using only relevant agents. "
        "Always include 'log'. Include 'diff' if there was a recent commit. "
        "Include 'dep' only if there is likely a dependency issue."
    )
    user = (
        f"Workflow: {ctx.workflow_name if ctx else 'unknown'}\n"
        f"Failed jobs: {ctx.failed_jobs if ctx else []}\n"
        f"Has diff: {bool(ctx.diff) if ctx else False}\n"
        f"Has deps: {bool(ctx.dependencies.get('content')) if ctx else False}\n"
        "Which agents should run?"
    )

    try:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, _gemini_json, system, user)
        agents = parsed.get("agents", ["log", "diff", "dep"])
    except Exception as exc:
        logger.warning("Triage failed, defaulting to all agents: %s", exc)
        agents = ["log", "diff", "dep"]

    _add_trace(run, "triage", f"Will run agents: {', '.join(agents)}")
    await _broadcast_trace(run)
    return agents


# ---------------------------------------------------------------------------
# Step 3: run_specialists
# ---------------------------------------------------------------------------

async def _run_specialists(run: HelixRun, agents_to_run: list[str]) -> list[AgentFinding]:
    _add_trace(run, "run_specialists", "Analysis swarm running in parallel…", TraceStatus.RUNNING)
    ctx = run.failure_context
    loop = asyncio.get_event_loop()

    async def _run_one(name: str) -> AgentFinding:
        try:
            if name == "log":
                finding = await loop.run_in_executor(None, LogAnalysisAgent().run, ctx.logs if ctx else "")
            elif name == "diff":
                finding = await loop.run_in_executor(None, DiffAnalysisAgent().run, ctx.diff if ctx else "")
            elif name == "dep":
                finding = await loop.run_in_executor(None, DependencyAgent().run, ctx.dependencies if ctx else {})
            else:
                return AgentFinding(agent_name=name, finding_type="unknown", details="Unknown agent", confidence=0.0)

            _add_trace(run, "run_specialists",
                       f"{name}_agent completed (confidence={finding.confidence:.0%})")
            await _broadcast_trace(run)
            return finding
        except Exception as exc:
            logger.exception("Agent '%s' failed: %s", name, exc)
            return AgentFinding(agent_name=name, finding_type="unknown", details=str(exc), confidence=0.0)

    findings = list(await asyncio.gather(*[_run_one(a) for a in agents_to_run]))
    return findings


# ---------------------------------------------------------------------------
# Step 4: diagnose
# ---------------------------------------------------------------------------

async def _diagnose(run: HelixRun, findings: list[AgentFinding]) -> Diagnosis:
    run.status = RunStatus.DIAGNOSING
    _add_trace(run, "diagnose", "Synthesising findings into diagnosis…", TraceStatus.RUNNING)
    ctx = run.failure_context

    findings_text = "\n\n".join(
        f"[{f.agent_name}] (confidence={f.confidence:.0%})\n{f.details}"
        for f in findings
    )
    system = (
        "You are the diagnosis engine for Helix, an autonomous CI/CD self-healing agent. "
        "Given specialist findings, produce a root-cause diagnosis of the CI/CD pipeline failure. "
        "IMPORTANT: Diagnose the user's failing GitHub Actions workflow — NOT Helix's internal runtime. "
        "If findings mention Gemini model errors, API keys, or Helix agent failures, treat those as "
        "Helix infrastructure issues (failure_type=ENV_ISSUE) separate from the original CI failure; "
        "prefer root causes from raw CI logs and workflow errors when available. "
        "Return JSON with keys:\n"
        "  failure_type: one of BUILD_ERROR|TEST_FAILURE|DEPENDENCY_CONFLICT|ENV_ISSUE|FLAKY_TEST|UNKNOWN\n"
        "  root_cause: clear 1-2 sentence explanation of why the CI pipeline failed\n"
        "  affected_files: list of file paths most likely involved\n"
        "  confidence: float 0.0-1.0\n"
        "Respond ONLY with the JSON object."
    )
    user = (
        f"Workflow: {ctx.workflow_name if ctx else 'unknown'}\n"
        f"Failed jobs: {ctx.failed_jobs if ctx else []}\n\n"
        f"Specialist findings:\n{findings_text}\n\nProduce the diagnosis."
    )

    try:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, _gemini_json, system, user)
        diagnosis = Diagnosis(
            failure_type=FailureType(parsed.get("failure_type", "UNKNOWN")),
            root_cause=parsed.get("root_cause", "Unknown root cause"),
            affected_files=parsed.get("affected_files", []),
            confidence=float(parsed.get("confidence", 0.5)),
            findings=findings,
        )
    except Exception as exc:
        logger.error("Diagnosis failed: %s", exc)
        diagnosis = Diagnosis(
            failure_type=FailureType.UNKNOWN,
            root_cause=f"Diagnosis error: {exc}",
            findings=findings,
            confidence=0.1,
        )

    run.diagnosis = diagnosis
    store.save_run(run)
    _add_trace(run, "diagnose",
               f"Diagnosed: {diagnosis.failure_type} (confidence={diagnosis.confidence:.0%})")
    await store.broadcast("diagnosis_ready", {"run_id": run.run_id, "diagnosis": diagnosis.model_dump()})
    return diagnosis


# ---------------------------------------------------------------------------
# Step 5: generate_fix
# ---------------------------------------------------------------------------

async def _generate_fix(run: HelixRun) -> Fix:
    run.status = RunStatus.FIXING
    run.attempts += 1
    _add_trace(run, "generate_fix", f"Generating fix (attempt {run.attempts})…", TraceStatus.RUNNING)
    store.save_run(run)

    ctx  = run.failure_context
    diag = run.diagnosis

    retry_context = ""
    if run.sandbox_output and not run.sandbox_output.get("success"):
        retry_context = (
            f"\n\nPrevious attempt #{run.attempts - 1} failed in sandbox:\n"
            f"Exit code: {run.sandbox_output.get('exit_code')}\n"
            f"Output:\n{run.sandbox_output.get('output', '')[-1000:]}\n"
            "Please try a different approach."
        )

    system = (
        "You are the fix generation engine for Helix. "
        "Given a CI failure, produce a minimal correct fix in unified diff format. "
        "IMPORTANT: You MUST always return a real patch that creates or modifies at least one file. "
        "If the error is a missing file, create it. If it's a bad dependency, fix it. "
        "Return ONLY a JSON object with these exact keys:\n"
        "  patch: a valid unified diff string starting with '--- a/filename' and '+++ b/filename'\n"
        "  explanation: 2-3 sentence plain-English explanation of the fix\n"
        "  files_changed: list of file paths modified or created\n"
        "  test_commands: list of shell commands to validate\n"
        "Example patch format:\n"
        "--- a/test_app.py\n+++ b/test_app.py\n@@ -0,0 +1,5 @@\n+def test_hello():\n+    assert True\n"
        "NEVER return an empty patch. NEVER return empty files_changed."
    )
    user = (
        f"Root cause: {diag.root_cause if diag else 'unknown'}\n"
        f"Failure type: {diag.failure_type if diag else 'UNKNOWN'}\n"
        f"Affected files: {diag.affected_files if diag else []}\n\n"
        f"CI Logs (excerpt):\n{(ctx.logs or '')[-3000:] if ctx else ''}\n\n"
        f"Git diff:\n{(ctx.diff or '')[:2000] if ctx else ''}\n\n"
        f"{retry_context}\n\n"
        "The CI logs show exactly what is missing or broken. "
        "Generate a concrete fix patch that resolves the failure. "
        "If a file is missing, create it with the correct content. "
        "Return valid JSON only."
    )

    try:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(None, _gemini_json, system, user)
        fix = Fix(
            patch=parsed.get("patch", ""),
            explanation=parsed.get("explanation", ""),
            files_changed=parsed.get("files_changed", []),
            test_commands=parsed.get("test_commands", []),
        )
        fix._root_cause = diag.root_cause if diag else ""  # type: ignore[attr-defined]
    except Exception as exc:
        logger.error("generate_fix failed: %s", exc)
        fix = Fix(patch="", explanation=f"Fix generation error: {exc}", files_changed=[], test_commands=[])

    run.fix = fix
    store.save_run(run)
    _add_trace(run, "generate_fix", f"Fix generated for {len(fix.files_changed)} file(s)")
    await store.broadcast("fix_ready", {"run_id": run.run_id, "fix": fix.model_dump()})
    return fix


# ---------------------------------------------------------------------------
# Step 6: validate
# ---------------------------------------------------------------------------

async def _validate(run: HelixRun) -> dict[str, Any]:
    run.status = RunStatus.VALIDATING
    _add_trace(run, "validate", "Running fix in Docker sandbox…", TraceStatus.RUNNING)
    store.save_run(run)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, run_in_sandbox, run.fix, run.failure_context)
    except Exception as exc:
        logger.exception("Sandbox raised: %s", exc)
        result = {"success": False, "output": str(exc), "exit_code": -1}

    run.sandbox_output = result
    store.save_run(run)
    success = result.get("success", False)
    _add_trace(
        run, "validate",
        f"Sandbox {'passed ✓' if success else 'failed ✗'} (exit={result.get('exit_code')})",
        TraceStatus.DONE if success else TraceStatus.FAILED,
    )
    await store.broadcast("sandbox_result", {"run_id": run.run_id, "sandbox_output": result})
    return result


# ---------------------------------------------------------------------------
# Step 7: open_pr
# ---------------------------------------------------------------------------

async def _open_pr(run: HelixRun) -> None:
    _add_trace(run, "open_pr", "Opening pull request on GitHub…", TraceStatus.RUNNING)
    ctx = run.failure_context
    loop = asyncio.get_event_loop()
    try:
        pr_url = await loop.run_in_executor(
            None,
            github_tools.open_pr,
            ctx.repo, ctx.branch, ctx.branch, run.fix, run.run_id,
        )
        run.pr_url = pr_url
        run.status = RunStatus.FIXED
        _add_trace(run, "open_pr", f"PR opened: {pr_url}")
    except Exception as exc:
        logger.exception("open_pr failed: %s", exc)
        run.status = RunStatus.ESCALATED
        _add_trace(run, "open_pr", f"Failed to open PR: {exc}", TraceStatus.FAILED)

    store.save_run(run)
    await store.broadcast("run_complete", run.model_dump())


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def run_helix(run: HelixRun) -> None:
    """
    Execute the full Helix self-healing pipeline for one run.
    Steps run sequentially; agents/GitHub calls run in parallel within each step.
    Retries fix generation up to MAX_RETRY_ATTEMPTS on sandbox failure.
    """
    logger.info("Starting Helix run %s for %s", run.run_id,
                run.failure_context.repo if run.failure_context else "?")
    try:
        # 1. Fetch context
        await _assemble_context(run)

        # 2. Triage
        agents_to_run = await _triage(run)

        # 3. Run specialists
        findings = await _run_specialists(run, agents_to_run)

        # 4. Diagnose
        await _diagnose(run, findings)

        # 5–8. Fix → validate → PR, with retry loop
        for attempt in range(1, settings.max_retry_attempts + 1):
            await _generate_fix(run)
            result = await _validate(run)

            if result.get("success"):
                await _open_pr(run)
                return

            # Sandbox failed
            if attempt < settings.max_retry_attempts:
                _add_trace(run, "retry_or_escalate",
                           f"Retrying… (attempt {attempt}/{settings.max_retry_attempts})",
                           TraceStatus.RUNNING)
                await _broadcast_trace(run)
            else:
                # All retries exhausted
                run.status = RunStatus.ESCALATED
                _add_trace(run, "retry_or_escalate",
                           f"All {settings.max_retry_attempts} attempts exhausted — escalating",
                           TraceStatus.FAILED)
                store.save_run(run)
                await store.broadcast("run_complete", run.model_dump())
                logger.warning("Run %s escalated after %d attempts", run.run_id, attempt)

    except Exception as exc:
        logger.exception("Pipeline error for run %s: %s", run.run_id, exc)
        run.status = RunStatus.ESCALATED
        store.save_run(run)
        await store.broadcast("run_complete", run.model_dump())
