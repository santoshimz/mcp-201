from __future__ import annotations

from dataclasses import dataclass

from security.key_policy import CredentialPolicyError, validate_credential_mode
from server.config import Settings


class CredentialResolutionError(RuntimeError):
    """Raised when Gemini credentials cannot be resolved safely."""


@dataclass(frozen=True)
class ResolvedCredential:
    mode: str
    api_key: str
    model: str


def resolve_gemini_credentials(
    *,
    credential_mode: str,
    gemini_api_key: str | None,
    model: str | None,
    settings: Settings,
) -> ResolvedCredential:
    decision = validate_credential_mode(credential_mode, gemini_api_key)
    active_model = (model or settings.image_model).strip() or settings.image_model

    if decision.uses_server_key:
        if not settings.server_gemini_api_key:
            raise CredentialResolutionError(
                "credentialMode=server is unavailable because the server Gemini key is not configured."
            )
        return ResolvedCredential(mode="server", api_key=settings.server_gemini_api_key, model=active_model)

    byok = (gemini_api_key or "").strip()
    if not byok:
        raise CredentialPolicyError("credentialMode=byok requires geminiApiKey.")
    return ResolvedCredential(mode="byok", api_key=byok, model=active_model)


def resolve_planner_credentials(
    *,
    credential_mode: str,
    gemini_api_key: str | None,
    settings: Settings,
) -> tuple[str | None, str]:
    if credential_mode == "byok" and gemini_api_key and gemini_api_key.strip():
        return gemini_api_key.strip(), "byok"
    if settings.server_gemini_api_key:
        return settings.server_gemini_api_key, "server"
    return None, "fallback"
