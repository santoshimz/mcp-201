from __future__ import annotations

from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from server.prompt_text import (
    COLORIZE_IMAGES_TOOL_DESCRIPTION,
    CROP_IMAGES_TOOL_DESCRIPTION,
    DEFAULT_COLORIZE_PROMPT,
    RUN_PROMPT_WORKFLOW_TOOL_DESCRIPTION,
)
from server.auth import RequestAuthMiddleware
from server.config import Settings
from server.tool_handlers import run_colorize_images, run_crop_images, run_prompt_workflow as run_prompt_workflow_handler


SETTINGS = Settings.from_env()
MCP = FastMCP(
    "mcp-201",
    host=SETTINGS.host,
    stateless_http=True,
    json_response=True,
)


@MCP.tool(description=CROP_IMAGES_TOOL_DESCRIPTION)
def crop_images(images: list[dict[str, str]]) -> dict[str, Any]:
    return run_crop_images({"images": images}, SETTINGS)


@MCP.tool(description=COLORIZE_IMAGES_TOOL_DESCRIPTION)
def colorize_images(
    images: list[dict[str, str]],
    credential_mode: str = "server",
    gemini_api_key: str | None = None,
    prompt: str = DEFAULT_COLORIZE_PROMPT,
    model: str | None = None,
) -> dict[str, Any]:
    return run_colorize_images(
        {
            "images": images,
            "credential_mode": credential_mode,
            "gemini_api_key": gemini_api_key,
            "prompt": prompt,
            "model": model,
        },
        SETTINGS,
    )


@MCP.tool(description=RUN_PROMPT_WORKFLOW_TOOL_DESCRIPTION)
def run_prompt_workflow(
    prompt: str,
    images: list[dict[str, str]],
    credential_mode: str = "server",
    gemini_api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return run_prompt_workflow_handler(
        {
            "prompt": prompt,
            "images": images,
            "credentialMode": credential_mode,
            "geminiApiKey": gemini_api_key,
            "model": model,
        },
        SETTINGS,
    )


async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def create_app(settings: Settings | None = None) -> Starlette:
    active_settings = settings or SETTINGS
    app = MCP.streamable_http_app()
    app.router.routes.append(Route("/healthz", healthz))
    app.add_middleware(RequestAuthMiddleware, settings=active_settings)
    return CORSMiddleware(
        app,
        allow_origins=list(active_settings.allowed_origins),
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Mcp-Session-Id"],
    )


app = create_app(SETTINGS)


def main() -> None:
    uvicorn.run("mcp_201_server:app", host=SETTINGS.host, port=SETTINGS.port, reload=False)


if __name__ == "__main__":
    main()
