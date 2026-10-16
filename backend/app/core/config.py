"""
ScopePilot AI — Application Configuration
Reads all settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional, List


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "ScopePilot AI"
    app_env: str = "development"
    secret_key: str = "changeme-please-use-a-secure-random-key"
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    max_upload_size_mb: int = 50

    # ── Supabase ─────────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "scopepilot-files"
    supabase_templates_bucket: str = "scopepilot-templates"
    supabase_sow_bucket: str = "scopepilot-sow-outputs"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = ""

    # ── AI Provider ──────────────────────────────────────────────────────────
    ai_provider: str = "google"  # openai | anthropic | google | ollama
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    google_api_key: str = ""
    google_model: str = "gemini-3.5-flash-lite"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # ── Document processing ──────────────────────────────────────────────────
    enable_ocr: bool = False
    ocr_language: str = "eng"
    libreoffice_path: str = "soffice"

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False

    # ── Logging ──────────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def ai_configured(self) -> bool:
        if self.ai_provider == "openai":
            return bool(self.openai_api_key)
        elif self.ai_provider == "anthropic":
            return bool(self.anthropic_api_key)
        elif self.ai_provider == "google":
            return bool(self.google_api_key)
        elif self.ai_provider == "ollama":
            return True  # Ollama runs locally
        return False

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
