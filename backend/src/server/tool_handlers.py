from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

from PIL import Image

from server.config import Settings
from server.credential_resolver import resolve_gemini_credentials, resolve_planner_credentials
from server.prompt_planner import PromptPlanningError, route_prompt
from server.request_models import (
    ColorizeImagesRequest,
    CropImagesRequest,
    ImageInput,
    PromptWorkflowRequest,
    ToolResponse,
    ToolResultImage,
)
from skills.colorize_images import DEFAULT_PROMPT, colorize_image_bytes, output_filename as colorized_name
from skills.crop_images import crop_image_bytes, output_filename as cropped_name


class ToolInputError(ValueError):
    """Raised when tool input validation fails."""


def _decode_image(image: ImageInput, settings: Settings) -> bytes:
    try:
        data = base64.b64decode(image.content_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ToolInputError(f"{image.filename} is not valid base64.") from exc

    if len(data) > settings.max_file_size_bytes:
        raise ToolInputError(f"{image.filename} exceeds the size limit.")

    try:
        with Image.open(BytesIO(data)) as candidate:
            candidate.verify()
    except Exception as exc:  # noqa: BLE001
        raise ToolInputError(f"{image.filename} is not a supported image.") from exc

    return data


def _encode_output(filename: str, image_bytes: bytes) -> ToolResultImage:
    return ToolResultImage(
        filename=filename,
        content_base64=base64.b64encode(image_bytes).decode("ascii"),
    )


def run_crop_images(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    request = CropImagesRequest.model_validate(payload)
    if len(request.images) > settings.max_images:
        raise ToolInputError(f"At most {settings.max_images} images are allowed.")

    outputs = []
    for image in request.images:
        cropped = crop_image_bytes(_decode_image(image, settings))
        outputs.append(_encode_output(cropped_name(image.filename), cropped))

    return ToolResponse(tool_name="crop_images", image_count=len(request.images), outputs=outputs).model_dump()


def run_colorize_images(payload: dict[str, Any], settings: Settings, *, client=None) -> dict[str, Any]:
    request = ColorizeImagesRequest.model_validate(payload)
    if len(request.images) > settings.max_images:
        raise ToolInputError(f"At most {settings.max_images} images are allowed.")

    credential = resolve_gemini_credentials(
        credential_mode=request.credential_mode,
        gemini_api_key=request.gemini_api_key.get_secret_value() if request.gemini_api_key else None,
        model=request.model,
        settings=settings,
    )

    outputs = []
    for image in request.images:
        colorized = colorize_image_bytes(
            _decode_image(image, settings),
            api_key=credential.api_key,
            model=credential.model,
            prompt=request.prompt,
            client=client,
        )
        outputs.append(_encode_output(colorized_name(image.filename), colorized))

    return ToolResponse(
        tool_name="colorize_images",
        credential_mode=credential.mode,
        image_count=len(request.images),
        outputs=outputs,
    ).model_dump()


def run_crop_then_colorize(payload: dict[str, Any], settings: Settings, *, client=None) -> dict[str, Any]:
    request = ColorizeImagesRequest.model_validate(payload)
    if len(request.images) > settings.max_images:
        raise ToolInputError(f"At most {settings.max_images} images are allowed.")

    credential = resolve_gemini_credentials(
        credential_mode=request.credential_mode,
        gemini_api_key=request.gemini_api_key.get_secret_value() if request.gemini_api_key else None,
        model=request.model,
        settings=settings,
    )

    outputs = []
    for image in request.images:
        source_bytes = _decode_image(image, settings)
        cropped = crop_image_bytes(source_bytes)
        cropped_filename = cropped_name(image.filename)
        colorized = colorize_image_bytes(
            cropped,
            api_key=credential.api_key,
            model=credential.model,
            prompt=request.prompt or DEFAULT_PROMPT,
            client=client,
        )
        outputs.append(_encode_output(cropped_filename, cropped))
        outputs.append(_encode_output(colorized_name(cropped_filename), colorized))

    return ToolResponse(
        tool_name="crop_then_colorize",
        credential_mode=credential.mode,
        image_count=len(request.images),
        outputs=outputs,
    ).model_dump()


def run_prompt_workflow(
    payload: dict[str, Any],
    settings: Settings,
    *,
    image_client=None,
    planner_client=None,
) -> dict[str, Any]:
    request = PromptWorkflowRequest.model_validate(payload)
    if len(request.images) > settings.max_images:
        raise ToolInputError(f"At most {settings.max_images} images are allowed.")

    planner_key, planner_mode = resolve_planner_credentials(
        credential_mode=request.credential_mode,
        gemini_api_key=request.gemini_api_key.get_secret_value() if request.gemini_api_key else None,
        settings=settings,
    )
    warnings: list[str] = []
    if planner_mode == "fallback":
        warnings.append("No Gemini key was available for AI planning. Using heuristic fallback.")

    try:
        selected_workflow, planning_warnings = route_prompt(
            request.prompt,
            settings=settings,
            api_key=planner_key,
            client=planner_client,
        )
        warnings.extend(planning_warnings)
    except PromptPlanningError as exc:
        raise ToolInputError(str(exc)) from exc

    forwarded_payload: dict[str, Any] = {
        "images": [image.model_dump() for image in request.images],
    }

    if selected_workflow != "crop_images":
        forwarded_payload["credentialMode"] = request.credential_mode
        if request.gemini_api_key is not None:
            forwarded_payload["geminiApiKey"] = request.gemini_api_key.get_secret_value()
        if request.model:
            forwarded_payload["model"] = request.model
        forwarded_payload["prompt"] = request.prompt

    if selected_workflow == "crop_images":
        result = run_crop_images(forwarded_payload, settings)
    elif selected_workflow == "colorize_images":
        result = run_colorize_images(forwarded_payload, settings, client=image_client)
    else:
        result = run_crop_then_colorize(forwarded_payload, settings, client=image_client)

    result["tool_name"] = "run_prompt_workflow"
    result["selected_workflow"] = selected_workflow
    result["warnings"] = [*result.get("warnings", []), *warnings]
    return result
