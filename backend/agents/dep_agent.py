"""
backend/agents/dep_agent.py
----------------------------
DependencyAgent — specialist agent that inspects the dependency manifest
(package.json or requirements.txt) for version conflicts, missing packages,
and incompatible combinations that could cause CI failures.
Uses Google Gemini. Returns a structured AgentFinding.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import google.generativeai as genai

from config import settings
from models import AgentFinding

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = (
    "You are a dependency conflict expert embedded inside Helix, an autonomous self-healing CI/CD agent. "
    "You will receive the contents of a dependency manifest (package.json or requirements.txt). "
    "Your task is to identify any version conflicts, missing packages, or incompatible combinations "
    "that could cause CI failures such as import errors, build failures, or test errors. "
    "Return a JSON object with these exact keys:\n"
    "  dep_type: 'npm' | 'pip' | 'unknown'\n"
    "  conflicts: list of strings, each describing a specific conflict or issue found\n"
    "  missing_packages: list of package names that may be missing or unlisted\n"
    "  recommendations: list of recommended version changes or additions\n"
    "  confidence: float 0.0-1.0 indicating how certain you are that deps caused the failure\n"
    "Respond ONLY with the JSON object, no prose, no markdown fences."
)


class DependencyAgent:
    """Analyses a dependency manifest and returns a structured AgentFinding."""

    def __init__(self) -> None:
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=SYSTEM_PROMPT,
        )

    def run(self, dependencies: dict[str, Any]) -> AgentFinding:
        """
        Analyse the *dependencies* dict (output of fetch_deps) using Gemini.
        Never raises — returns a low-confidence finding on error.
        """
        dep_content = dependencies.get("content", "")
        dep_type = dependencies.get("type", "unknown")

        if not dep_content or not dep_content.strip():
            return self._empty_finding("No dependency manifest content available")

        try:
            prompt = (
                f"The CI pipeline failed. Analyse this {dep_type} dependency manifest "
                f"for any issues:\n\n```\n{dep_content}\n```"
            )
            response = self._model.generate_content(prompt)
            raw = response.text.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            parsed = json.loads(raw)

            conflicts = parsed.get("conflicts", [])
            missing = parsed.get("missing_packages", [])
            recs = parsed.get("recommendations", [])

            details = (
                f"Dependency type: {parsed.get('dep_type', dep_type)}\n"
                f"Conflicts found: {'; '.join(conflicts) if conflicts else 'none'}\n"
                f"Missing packages: {', '.join(missing) if missing else 'none'}\n"
                f"Recommendations: {'; '.join(recs) if recs else 'none'}"
            )
            confidence = float(parsed.get("confidence", 0.5))
            logger.info("DepAgent completed — conflicts=%d confidence=%.2f",
                        len(conflicts), confidence)
            return AgentFinding(
                agent_name="dep_agent",
                finding_type="dependency_analysis",
                details=details,
                confidence=min(max(confidence, 0.0), 1.0),
            )

        except json.JSONDecodeError as exc:
            logger.error("DepAgent: Gemini returned non-JSON response: %s", exc)
            return self._empty_finding(f"Could not parse Gemini response: {exc}")
        except Exception as exc:
            logger.exception("DepAgent: unexpected error")
            return self._empty_finding(f"Agent error: {exc}")

    @staticmethod
    def _empty_finding(reason: str) -> AgentFinding:
        return AgentFinding(
            agent_name="dep_agent",
            finding_type="dependency_analysis",
            details=reason,
            confidence=0.1,
        )
