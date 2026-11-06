from ipaddress import ip_address
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    data_mode: Literal["fixtures", "live"] = "fixtures"
    app_env: str = "development"
    database_url: str = "sqlite:///./stocker.db"
    llm_base_url: str = "http://127.0.0.1:4000/v1"
    llm_model: str = ""
    llm_api_key: str = Field(default="", repr=False)
    ai_config_file: Path | None = None
    llm_timeout: float = Field(default=600, gt=0, le=3600)
    llm_max_tokens: int = Field(default=8192, ge=128, le=65536)
    llm_context_window_tokens: int = Field(default=131072, ge=4096, le=262144)
    llm_run_output_tokens: int = Field(default=196608, ge=128, le=1572864)
    llm_run_total_tokens: int = Field(default=1048576, ge=128, le=8388608)
    llm_run_context_bytes: int = Field(default=8388608, ge=4096, le=67108864)
    research_run_timeout: float = Field(default=7200, gt=0, le=86400)

    @model_validator(mode="after")
    def model_budgets(self):
        if self.llm_max_tokens + 2048 >= self.llm_context_window_tokens:
            raise ValueError("Output budget must leave input room and a context safety margin")
        if self.llm_run_output_tokens < self.llm_max_tokens:
            raise ValueError("Run output budget must cover at least one response")
        if self.llm_run_total_tokens < self.llm_max_tokens:
            raise ValueError("Run total token budget must cover at least one response")
        return self

    sec_user_agent: str = ""
    finnhub_api_key: str = ""
    alpha_vantage_api_key: str = ""
    fred_api_key: str = ""
    history_provider: Literal["auto", "yfinance", "alpha_vantage"] = "auto"
    bank_of_canada_enabled: bool = True

    @field_validator("llm_base_url")
    @classmethod
    def model_endpoint(cls, value):
        parsed = urlparse(value)
        local_http = parsed.hostname in {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
        try:
            address = ip_address(parsed.hostname or "")
            local_http = local_http or (address.version == 4 and address.is_link_local)
        except ValueError:
            pass
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (parsed.scheme == "http" and local_http))
        ):
            raise ValueError(
                "Model endpoint must be HTTPS or loopback/link-local IPv4 or host.docker.internal HTTP without embedded credentials"
            )
        return value
