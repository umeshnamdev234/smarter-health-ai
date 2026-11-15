"""Request / response models."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ImageInput(BaseModel):
    mime_type: str = Field("image/jpeg", examples=["image/png"])
    data: str = Field(..., description="Base64-encoded image (a data: URL is also accepted)")

    @model_validator(mode="before")
    @classmethod
    def strip_data_url(cls, values):
        # Accept "data:image/png;base64,AAAA..." and split it into mime_type + data
        if isinstance(values, dict):
            data = values.get("data", "")
            if isinstance(data, str) and data.startswith("data:") and "," in data:
                header, b64 = data.split(",", 1)
                values = {**values, "data": b64, "mime_type": header[5:].split(";")[0] or values.get("mime_type")}
        return values

    @field_validator("mime_type")
    @classmethod
    def must_be_image(cls, v: str) -> str:
        if not v.startswith("image/"):
            raise ValueError("mime_type must be an image/* type")
        return v

    @property
    def approx_bytes(self) -> int:
        return len(self.data) * 3 // 4


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = ""
    images: list[ImageInput] = Field(default_factory=list)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="Conversation so far; last message must be from the user")
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    model: Optional[str] = Field(None, description="Override the configured model")

    @model_validator(mode="after")
    def last_is_user(self):
        last = self.messages[-1]
        if last.role != "user":
            raise ValueError("last message must have role 'user'")
        if not last.content.strip() and not last.images:
            raise ValueError("last message must contain text or an image")
        return self


class ChatResponse(BaseModel):
    reply: str
    model: str
    emergency: bool = False
    emergency_notice: Optional[str] = None
    usage: Optional[dict] = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model: str
    model_server: str
    model_server_reachable: bool
    model_available: bool
    database_reachable: bool


class RecommendRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1, description="The conversation to base suggestions on")
    city: Optional[str] = None
    language: Optional[str] = None
    teleconsult_only: bool = False
    limit: int = Field(5, ge=1, le=20)
    # Optional: reuse a previous triage (e.g. when only filters changed) to skip the model call
    specialties: Optional[list[str]] = Field(None, max_length=3)
    conditions: list[str] = Field(default_factory=list, max_length=4)
    urgency: Optional[Literal["routine", "soon", "urgent", "emergency"]] = None

    @model_validator(mode="after")
    def has_user_input(self):
        if not any(m.role == "user" and (m.content.strip() or m.images) for m in self.messages):
            raise ValueError("conversation must include at least one user message")
        return self
