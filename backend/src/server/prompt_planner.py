from __future__ import annotations

import json
import re

from server.config import Settings
from server.prompt_text import build_planner_prompt


class PromptPlanningError(ValueError):
    """Raised when the prompt cannot be mapped to a supported workflow."""


WORKFLOW_NAMES = {"crop_images", "colorize_images", "crop_then_colorize"}

CROP_PATTERNS = (
    r"\bcrop\b",
    r"visible frame",
    r"remove (?:youtube )?(?:ui|overlay|overlays|controls?)",
    r"remove black bars?",
    r"clean screenshot",
    r"trim screenshot",
)

COLORIZE_PATTERNS = (
    r"\bcolori[sz]e\b",
    r"black[\s-]and[\s-]white",
    r"add color",
    r"realistic(?:ally)? color",
    r"restore color",
)


def _matches_any(prompt: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, prompt) for pattern in patterns)


def _heuristic_route(prompt: str) -> tuple[str, list[str]]:
    normalized = " ".join(prompt.strip().lower().split())
    has_crop = _matches_any(normalized, CROP_PATTERNS)
    has_colorize = _matches_any(normalized, COLORIZE_PATTERNS)

    if has_crop and has_colorize:
        return "crop_then_colorize", ["Fell back to heuristic planner."]
    if has_crop:
        return "crop_images", ["Fell back to heuristic planner."]
    if has_colorize:
        return "colorize_images", ["Fell back to heuristic planner."]
    raise PromptPlanningError("Prompt did not clearly match a supported workflow.")


def create_default_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _extract_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    fragments: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            part_text = getattr(part, "text", None)
            if part_text:
                fragments.append(part_text)
    return "\n".join(fragments).strip()


def _parse_planner_output(text: str) -> tuple[str, list[str]]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise PromptPlanningError("Planner did not return JSON.")
    payload = json.loads(text[start : end + 1])
    workflow = str(payload.get("workflow", "")).strip()
    if workflow not in WORKFLOW_NAMES:
        raise PromptPlanningError(f"Planner returned unsupported workflow: {workflow!r}")
    confidence_value = payload.get("confidence", 0.0)
    if isinstance(confidence_value, str):
        normalized_confidence = confidence_value.strip().lower()
        confidence_lookup = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.9,
        }
        confidence = confidence_lookup.get(normalized_confidence, 0.0)
    else:
        confidence = float(confidence_value)
    reason = str(payload.get("reasoning_summary", "")).strip()
    warnings: list[str] = []
    if confidence < 0.35:
        warnings.append(f"Planner confidence was low ({confidence:.2f}).")
    if reason:
        warnings.append(f"AI planner: {reason}")
    return workflow, warnings


def route_prompt(
    prompt: str,
    *,
    settings: Settings,
    api_key: str | None,
    client=None,
) -> tuple[str, list[str]]:
    if not api_key:
        return _heuristic_route(prompt)

    planner_prompt = build_planner_prompt(prompt)

    try:
        active_client = client or create_default_client(api_key)
        response = active_client.models.generate_content(
            model=settings.planner_model,
            contents=[planner_prompt],
        )
        return _parse_planner_output(_extract_text(response))
    except Exception:
        return _heuristic_route(prompt)
