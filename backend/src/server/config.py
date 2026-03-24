from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_secret_file(path: str | None) -> str | None:
    if not path:
        return None
    secret_path = Path(path).expanduser()
    if not secret_path.exists():
        return None
    return secret_path.read_text(encoding="utf-8").strip()


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8010
    max_images: int = 5
    max_file_size_bytes: int = 6 * 1024 * 1024
    require_auth: bool = False
    auth_token: str | None = None
    allowed_origins: tuple[str, ...] = ("http://localhost:3004",)
    server_gemini_api_key: str | None = None
    planner_model: str = "gemini-2.5-flash"
    image_model: str = "gemini-3.1-flash-image-preview"

    @classmethod
    def from_env(cls) -> "Settings":
        secret_file_value = _read_secret_file(os.environ.get("MCP_201_SERVER_GEMINI_API_KEY_FILE"))
        server_key = os.environ.get("MCP_201_SERVER_GEMINI_API_KEY", "").strip() or secret_file_value
        origins = tuple(
            origin.strip()
            for origin in os.environ.get("MCP_201_ALLOWED_ORIGINS", "http://localhost:3004").split(",")
            if origin.strip()
        )
        require_auth = os.environ.get("MCP_201_REQUIRE_AUTH", "false").strip().lower() == "true"
        auth_token = os.environ.get("MCP_201_AUTH_TOKEN", "").strip() or None

        return cls(
            host=os.environ.get("MCP_201_HOST", "0.0.0.0").strip() or "0.0.0.0",
            port=int(os.environ.get("MCP_201_PORT") or os.environ.get("PORT") or "8010"),
            max_images=int(os.environ.get("MCP_201_MAX_IMAGES", "5")),
            max_file_size_bytes=int(os.environ.get("MCP_201_MAX_FILE_SIZE_BYTES", str(6 * 1024 * 1024))),
            require_auth=require_auth,
            auth_token=auth_token,
            allowed_origins=origins or ("http://localhost:3004",),
            server_gemini_api_key=server_key,
            planner_model=os.environ.get("MCP_201_PLANNER_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
            image_model=os.environ.get(
                "MCP_201_IMAGE_MODEL",
                "gemini-3.1-flash-image-preview",
            ).strip()
            or "gemini-3.1-flash-image-preview",
        )
