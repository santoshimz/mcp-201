from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ImageInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        lowered = value.lower()
        if not any(lowered.endswith(suffix) for suffix in ALLOWED_SUFFIXES):
            raise ValueError("filename must end with .jpg, .jpeg, .png, or .webp")
        if "/" in value or "\\" in value:
            raise ValueError("filename must not contain path separators")
        return value


class CropImagesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    images: list[ImageInput]

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[ImageInput]) -> list[ImageInput]:
        if not value:
            raise ValueError("At least one image is required.")
        return value


class PromptWorkflowRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prompt: str = Field(min_length=1)
    images: list[ImageInput]
    credential_mode: Literal["server", "byok"] = Field(default="server", alias="credentialMode")
    gemini_api_key: SecretStr | None = Field(default=None, alias="geminiApiKey")
    model: str | None = None

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[ImageInput]) -> list[ImageInput]:
        if not value:
            raise ValueError("At least one image is required.")
        return value

    @model_validator(mode="after")
    def validate_credential_fields(self) -> "PromptWorkflowRequest":
        has_key = self.gemini_api_key is not None and bool(self.gemini_api_key.get_secret_value().strip())
        if self.credential_mode == "server" and has_key:
            raise ValueError("credentialMode=server cannot include geminiApiKey.")
        return self


class ColorizeImagesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    images: list[ImageInput]
    credential_mode: Literal["server", "byok"] = Field(alias="credentialMode")
    gemini_api_key: SecretStr | None = Field(default=None, alias="geminiApiKey")
    prompt: str = Field(
        default=(
            "Colorize this black and white photo realistically. Preserve the framing, people, "
            "objects, expressions, and scene details. Do not add or remove anything."
        )
    )
    model: str | None = None

    @field_validator("images")
    @classmethod
    def validate_images(cls, value: list[ImageInput]) -> list[ImageInput]:
        if not value:
            raise ValueError("At least one image is required.")
        return value

    @model_validator(mode="after")
    def validate_credential_fields(self) -> "ColorizeImagesRequest":
        has_key = self.gemini_api_key is not None and bool(self.gemini_api_key.get_secret_value().strip())
        if self.credential_mode == "server" and has_key:
            raise ValueError("credentialMode=server cannot include geminiApiKey.")
        if self.credential_mode == "byok" and not has_key:
            raise ValueError("credentialMode=byok requires geminiApiKey.")
        return self


class ToolResultImage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    filename: str
    content_base64: str
    media_type: str = "image/jpeg"


class ToolResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    tool_name: str
    credential_mode: str | None = None
    selected_workflow: str | None = None
    image_count: int
    outputs: list[ToolResultImage]
    warnings: list[str] = Field(default_factory=list)
