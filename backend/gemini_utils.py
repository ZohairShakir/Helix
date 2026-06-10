"""
backend/gemini_utils.py
-----------------------
Utility for calling Google Gemini API.
"""

from __future__ import annotations

import google.generativeai as genai
from config import settings

_model = None


def _get_model():
    """Get or create the Gemini model (singleton)."""
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(model_name="gemini-2.5-flash-lite")
    return _model


def generate_text(system_prompt: str, user_prompt: str) -> str:
    """Generate text using Google Gemini API."""
    model = _get_model()
    response = model.generate_content(
        user_prompt,
        system_instruction=system_prompt,
    )
    return response.text