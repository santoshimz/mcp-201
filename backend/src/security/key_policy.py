from __future__ import annotations

from dataclasses import dataclass


class CredentialPolicyError(ValueError):
    """Raised when a request violates the credential policy."""


@dataclass(frozen=True)
class CredentialPolicyDecision:
    mode: str
    uses_server_key: bool
    uses_byok: bool


def validate_credential_mode(mode: str, gemini_api_key: str | None) -> CredentialPolicyDecision:
    normalized = mode.strip().lower()
    has_byok = bool(gemini_api_key and gemini_api_key.strip())

    if normalized not in {"server", "byok"}:
        raise CredentialPolicyError("credentialMode must be either 'server' or 'byok'.")
    if normalized == "server" and has_byok:
        raise CredentialPolicyError("credentialMode=server cannot include geminiApiKey.")
    if normalized == "byok" and not has_byok:
        raise CredentialPolicyError("credentialMode=byok requires geminiApiKey.")

    return CredentialPolicyDecision(
        mode=normalized,
        uses_server_key=normalized == "server",
        uses_byok=normalized == "byok",
    )
