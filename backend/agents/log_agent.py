"""
backend/agents/log_agent.py
----------------------------
LogAnalysisAgent — specialist agent that reads raw CI log output
and uses Google Gemini to extract the root error, file location, and stack trace summary.
Returns a structured AgentFinding for consumption by the orchestrator.
"""

from __future__ import annotations

import json
import logging

import google.generativeai as genai

from config import settings
from models import AgentFinding

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)

SYSTEM_PROMPT = (
    "You are an expert CI/CD log analyzer embedded inside Helix, an autonomous self-healing agent. "
    "Your job is to extract signal from noisy CI log output. Focus exclusively on the ROOT error — "
    "ignore unrelated warnings, deprecation notices, and retry noise. "
    "Be concise and structured. Return a JSON object with these exact keys:\n"
    "  error_type: short category string (e.g. 'ImportError', 'AssertionError', 'SyntaxError', 'OOMKilled')\n"
    "  error_message: the exact error message from the log\n"
    "  file: filename and line number where the error occurred (or 'unknown')\n"
    "  stack_trace_summary: 2-3 sentence summary of the call chain\n"
    "  confidence: float 0.0-1.0 indicating how certain you are about the root cause\n"
    "Respond ONLY with the JSON object, no prose, no markdown fences."
)


class LogAnalysisAgent:
    """Analyses raw CI log text and returns a structured AgentFinding."""

    def __init__(self) -> None:
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=SYSTEM_PROMPT,
        )

    def run(self, logs: str) -> AgentFinding:
        """
        Analyse *logs* using Gemini and return an AgentFinding.
        Never raises — returns a low-confidence finding on error.
        """
        if not logs or not logs.strip():
            return self._empty_finding("No log content provided")

        try:
            prompt = f"Analyse the following CI logs and extract the root error:\n\n```\n{logs}\n```"
            response = self._model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if Gemini wraps the JSON
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            parsed = json.loads(raw)

            details = (
                f"Error type: {parsed.get('error_type', 'unknown')}\n"
                f"Message: {parsed.get('error_message', '')}\n"
                f"Location: {parsed.get('file', 'unknown')}\n"
                f"Stack summary: {parsed.get('stack_trace_summary', '')}"
            )
            confidence = float(parsed.get("confidence", 0.7))
            logger.info("LogAgent completed — error_type=%s confidence=%.2f",
                        parsed.get("error_type"), confidence)
            return AgentFinding(
                agent_name="log_agent",
                finding_type="log_analysis",
                details=details,
                confidence=min(max(confidence, 0.0), 1.0),
            )

        except json.JSONDecodeError as exc:
            logger.error("LogAgent: Gemini returned non-JSON response: %s", exc)
            return self._empty_finding(f"Could not parse Gemini response: {exc}")
        except Exception as exc:
            logger.exception("LogAgent: unexpected error")
            return self._empty_finding(f"Agent error: {exc}")

    @staticmethod
    def _empty_finding(reason: str) -> AgentFinding:
        return AgentFinding(
            agent_name="log_agent",
            finding_type="log_analysis",
            details=reason,
            confidence=0.1,
        )
