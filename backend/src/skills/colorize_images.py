from __future__ import annotations

from io import BytesIO

from PIL import Image
from server.prompt_text import DEFAULT_COLORIZE_PROMPT


DEFAULT_PROMPT = DEFAULT_COLORIZE_PROMPT


def create_default_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def collect_generated_images(response) -> list[tuple[bytes, str]]:
    generated: list[tuple[bytes, str]] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is None:
                continue
            payload = getattr(inline_data, "data", None)
            mime_type = getattr(inline_data, "mime_type", "image/png")
            if payload and str(mime_type).startswith("image/"):
                generated.append((payload, mime_type))
    return generated


def collect_response_text(response) -> str:
    fragments: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            text = getattr(part, "text", None)
            if text:
                fragments.append(text)
    return "\n".join(fragments).strip()


def colorize_image_bytes(
    image_bytes: bytes,
    *,
    api_key: str,
    model: str,
    prompt: str = DEFAULT_PROMPT,
    client=None,
) -> bytes:
    active_client = client or create_default_client(api_key)

    with Image.open(BytesIO(image_bytes)) as image:
        source_image = image.convert("RGB")
        response = active_client.models.generate_content(
            model=model,
            contents=[prompt, source_image],
        )

    generated = collect_generated_images(response)
    if not generated:
        response_text = collect_response_text(response)
        detail = f" Response text: {response_text}" if response_text else ""
        raise RuntimeError(f"Gemini response did not include an image.{detail}")

    generated_bytes, _mime_type = generated[0]
    with Image.open(BytesIO(generated_bytes)) as result:
        with BytesIO() as output:
            result.convert("RGB").save(output, format="JPEG", quality=95, optimize=True)
            return output.getvalue()


def output_filename(source_name: str) -> str:
    stem = source_name.rsplit(".", 1)[0]
    return f"{stem}-colorized.jpg"
