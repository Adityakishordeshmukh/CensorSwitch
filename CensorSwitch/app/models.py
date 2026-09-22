import time
import uuid
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    api_key: str = Field(..., description="Identifies the calling client/app")
    prompt: str
    preferred_provider: str | None = None  # optional override, e.g. "openai"


class ChatResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    answer: str
    provider: str
    cached: bool
    latency_ms: float
    timestamp: float = Field(default_factory=time.time)
