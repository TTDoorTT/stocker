"""Local model preferences; private atomic storage, immutable per-operation settings."""

import json
import os
import tempfile
from pathlib import Path
from threading import BoundedSemaphore, RLock

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.core.config import ROOT, Settings


class AIInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(min_length=1, max_length=2048)
    model_id: str = Field(min_length=1, max_length=200)
    api_key: SecretStr | None = Field(default=None)

    @field_validator("base_url", "model_id")
    @classmethod
    def clean_text(cls, value):
        if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("Whitespace and control characters are not allowed")
        return value

    @field_validator("base_url")
    @classmethod
    def endpoint(cls, value):
        return Settings.model_endpoint(value)

    @field_validator("api_key")
    @classmethod
    def clean_key(cls, value):
        if value is not None:
            key = value.get_secret_value()
            if len(key) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in key):
                raise ValueError("Invalid authentication key")
        return value


class AIStatus(BaseModel):
    base_url: str
    model_id: str
    has_api_key: bool
    configured: bool
    source: str


class ConnectionResult(BaseModel):
    ok: bool
    message: str


class AIConfiguration:
    def __init__(self, settings: Settings):
        self.environment = settings.model_copy(deep=True)
        self.path = settings.ai_config_file or ROOT / ".ai-settings" / "config.json"
        self.lock = RLock()
        self.probe_slot = BoundedSemaphore(1)
        self.saved: AIInput | None = None
        if self.path.exists():
            try:
                self.saved = AIInput.model_validate_json(self.path.read_text())
                if self.saved.api_key is None:
                    raise ValueError("Saved key must be explicit")
                self.path.chmod(0o600)
            except (OSError, ValueError):
                raise RuntimeError("Cannot load private AI configuration; restore it from backup") from None

    def current(self) -> Settings:
        with self.lock:
            settings = self.environment.model_copy(deep=True)
            if self.saved is not None:
                settings.llm_base_url = self.saved.base_url
                settings.llm_model = self.saved.model_id
                settings.llm_api_key = self.saved.api_key.get_secret_value()
            return settings

    def status(self) -> AIStatus:
        with self.lock:
            settings = self.current()
            return AIStatus(
                base_url=settings.llm_base_url,
                model_id=settings.llm_model,
                has_api_key=bool(settings.llm_api_key),
                configured=bool(settings.llm_model),
                source="saved" if self.saved else "environment",
            )

    def candidate(self, body: AIInput) -> AIInput:
        current = self.current()
        if body.api_key is None:
            if body.base_url.rstrip("/") != current.llm_base_url.rstrip("/"):
                raise ValueError("Enter a new API key or explicitly choose no key for a changed endpoint")
            return body.model_copy(update={"api_key": SecretStr(current.llm_api_key)})
        return body

    def save(self, body: AIInput) -> AIStatus:
        with self.lock:
            candidate = self.candidate(body)
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.path.parent.chmod(0o700)
            descriptor, temporary = tempfile.mkstemp(dir=self.path.parent)
            try:
                with os.fdopen(descriptor, "w") as stream:
                    json.dump(
                        {
                            "base_url": candidate.base_url,
                            "model_id": candidate.model_id,
                            "api_key": candidate.api_key.get_secret_value(),
                        },
                        stream,
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            self.saved = candidate
            return self.status()

    def reset(self) -> AIStatus:
        with self.lock:
            self.path.unlink(missing_ok=True)
            self.saved = None
            return self.status()

    def test(self, body: AIInput) -> ConnectionResult:
        candidate = self.candidate(body)
        if not self.probe_slot.acquire(blocking=False):
            return ConnectionResult(ok=False, message="A connection test is already running")
        try:
            headers = {}
            key = candidate.api_key.get_secret_value()
            if key:
                headers["Authorization"] = f"Bearer {key}"
            with httpx.Client(
                timeout=httpx.Timeout(20, connect=5), follow_redirects=False, trust_env=False
            ) as client:
                response = client.post(
                    candidate.base_url.rstrip("/") + "/chat/completions",
                    headers=headers,
                    json={
                        "model": candidate.model_id,
                        "messages": [{"role": "user", "content": "Reply OK"}],
                        "max_tokens": 128,
                    },
                )
                if response.status_code != 200:
                    return ConnectionResult(
                        ok=False, message=f"Model endpoint returned HTTP {response.status_code}"
                    )
                result = response.json()
                if not isinstance(result["choices"][0]["message"], dict):
                    raise ValueError("Invalid response")
            return ConnectionResult(
                ok=True, message="Model responded successfully. This does not verify research quality."
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            return ConnectionResult(
                ok=False,
                message="Connection failed or response was not OpenAI-compatible. Check the URL, model, key and Docker host networking.",
            )
        finally:
            self.probe_slot.release()
