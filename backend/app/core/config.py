from ipaddress import ip_address
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    data_mode: Literal["fixtures", "live"] = "fixtures"
    app_env: str = "development"
    database_url: str = "sqlite:///./stockscope.db"
    llm_base_url: str = "http://127.0.0.1:4000/v1"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout: float = Field(default=45, gt=0, le=120)
    llm_max_tokens: int = Field(default=2500, ge=128, le=4000)
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
        local_http = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
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
                "Model endpoint must be HTTPS or loopback/link-local IPv4 HTTP without embedded credentials"
            )
        return value
