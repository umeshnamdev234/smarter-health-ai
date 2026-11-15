"""App configuration, loaded from environment variables / .env file."""
import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Model server (any OpenAI-compatible endpoint) ---
    # Local Ollama:          http://localhost:11434/v1
    # HF Inference Endpoint: https://<name>.endpoints.huggingface.cloud/v1
    # vLLM on EC2 / Vertex:  http://<host>:8000/v1
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""          # empty for local Ollama; HF token / cloud key otherwise
    llm_model: str = "medgemma"
    llm_timeout_s: float = 300.0

    default_temperature: float = 0.4
    default_max_tokens: int = 1024

    # --- API ---
    # comma-separated (http://a,http://b) or a JSON list
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3100", "http://127.0.0.1:3100"]
    app_api_key: str = ""          # if set, clients must send header X-API-Key

    # --- Doctor directory: PostgreSQL (minikube, via scripts/db-tunnel.sh) ---
    database_url: str = "postgresql://smarter_health@localhost:15432/smarter_health"
    admin_api_key: str = ""        # enables PUT/DELETE /api/doctors/{id} (header X-Admin-Key)

    # --- Limits ---
    max_image_mb: float = 10.0
    max_images_per_message: int = 4

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
