"""
backend/agents/diff_agent.py
-----------------------------
DiffAnalysisAgent — examines git diff for suspicious changes.
"""

from __future__ import annotations

import json
import logging

from gemini_utils import generate_text
from models import AgentFinding

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert code reviewer embedded inside Helix, an autonomous self-healing CI/CD agent. "
    "You will receive a git unified diff. Your task is to determine which specific change in the diff "
    "most likely caused a CI pipeline failure. "
    "Return a JSON object with these exact keys:\n"
    "  files_changed: list of filenames that were modified\n"
    "  suspicious_change: a short description of the single most suspicious change\n"
    "  reasoning: 2-4 sentence explanation of why that change could cause a CI failure\n"
    "  affected_lines: list of line numbers or line ranges that are problematic (strings like '42' or '12-18')\n"
    "  confidence: float 0.0-1.0 indicating how certain you are\n"
    "Respond ONLY with the JSON object, no prose, no markdown fences."
)


class DiffAnalysisAgent:
    def run(self, diff: str) -> AgentFinding:
        if not diff or not diff.strip():
            return self._empty_finding("No diff content provided")

        try:
            prompt = (
                "The CI pipeline failed after this commit. "
                "Identify the most likely culprit change:\n\n"
                f"```diff\n{diff}\n```"
            )
            raw = generate_text(SYSTEM_PROMPT, prompt)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            parsed = json.loads(raw.strip())
            files = parsed.get("files_changed", [])
            details = (
                f"Files changed: {', '.join(files) if files else 'unknown'}\n"
                f"Suspicious change: {parsed.get('suspicious_change', '')}\n"
                f"Reasoning: {parsed.get('reasoning', '')}\n"
                f"Affected lines: {', '.join(parsed.get('affected_lines', []))}"
            )
            confidence = float(parsed.get("confidence", 0.6))
            return AgentFinding(
                agent_name="diff_agent",
                finding_type="diff_analysis",
                details=details,
                confidence=min(max(confidence, 0.0), 1.0),
            )

        except Exception as exc:
            logger.exception("DiffAgent: unexpected error")
            return self._empty_finding(f"Agent error: {exc}")

    @staticmethod
    def _empty_finding(reason: str) -> AgentFinding:
        return AgentFinding(
            agent_name="diff_agent",
            finding_type="diff_analysis",
            details=reason,
            confidence=0.1,
        )
