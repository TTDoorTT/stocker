"""Offline tests for local QA origins and filing claim length."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.modules.research import claim_review
from app.modules.research.claim_review import (
    MAX_CLAIM_CHARS,
    screen_filing_claims,
)
from app.modules.research.schemas import Claim

PATH = "/api/industries/ai-computing/sections/outlook/generate"


def settings(tmp_path, **extra):
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/qa.db",
        ai_config_file=tmp_path / "private" / "config.json",
        **extra,
    )


def test_default_rejects_qa_origin_but_keeps_original(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.post(PATH, headers={"origin": "http://localhost:5174"}).status_code == 403
        assert client.post(PATH, headers={"origin": "http://localhost:5173"}).status_code == 422


def test_explicit_loopback_origin_allowed_for_post_and_cors(tmp_path):
    cfg = settings(
        tmp_path,
        extra_frontend_origins=("http://localhost:5174,http://127.0.0.1:5174"),
    )
    with TestClient(create_app(cfg)) as client:
        for origin in (
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ):
            response = client.post(PATH, headers={"origin": origin})
            assert response.status_code == 422

            preflight = client.options(
                PATH,
                headers={
                    "origin": origin,
                    "access-control-request-method": "POST",
                },
            )
            assert preflight.status_code == 200
            assert preflight.headers["access-control-allow-origin"] == origin

        assert client.post(PATH, headers={"origin": "http://evil.test:5174"}).status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://0.0.0.0:5174",
        "http://192.168.1.2:5174",
        "https://evil.test:5174",
        "http://localhost:5174/path",
        "http://localhost:5174/",
        "http://localhost:5174,",
        "http://localhost:0",
        "http://localhost:99999",
        "http://localhost:5174,http://localhost:5174",
    ],
)
def test_invalid_origins_rejected(tmp_path, origin):
    with pytest.raises(ValueError):
        settings(tmp_path, extra_frontend_origins=origin)


@pytest.mark.parametrize("size", [601, 2000])
def test_schema_bounded_claims_are_reviewed(monkeypatch, size):
    assert MAX_CLAIM_CHARS == 2000

    body = "x" * size
    Claim(text=body)
    calls = []

    class Reviewer:
        def __init__(self, configuration):
            pass

        def complete(self, stage, context, schema, tools):
            assert stage == "claim_review"
            assert context["claims"][0]["text"] == body
            calls.append(stage)
            return {
                "assessments": [
                    {
                        "claim_index": 0,
                        "verdict": "supported",
                        "supporting_evidence_ids": ["ev-qa"],
                        "reason": "The provided issuer passage contains the supported statement.",
                    }
                ]
            }

    monkeypatch.setattr(claim_review, "ModelClient", Reviewer)

    evidence = [
        {
            "evidence_id": "ev-qa",
            "symbol": "NVDA",
            "field": "sec_10k_excerpt_technology",
            "source_url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm",
            "value": "issuer text (untrusted): The company describes technical operations and dependent production systems.",
        }
    ]

    cfg = Settings(_env_file=None, llm_model="fixture-reviewer")

    result = screen_filing_claims(
        [
            {
                "text": body,
                "evidence_ids": ["ev-qa"],
                "value": None,
                "calculation_ids": [],
            }
        ],
        evidence,
        cfg,
    )

    assert result["status"] == "model_screened"
    assert calls == ["claim_review"]


def test_above_schema_limit_fails_before_model(monkeypatch):
    class Forbidden:
        def __init__(self, configuration):
            raise AssertionError("Model should not be called")

    monkeypatch.setattr(claim_review, "ModelClient", Forbidden)

    with pytest.raises(ValueError, match="bounded"):
        screen_filing_claims(
            [
                {
                    "text": "x" * 2001,
                    "evidence_ids": ["ev-qa"],
                    "calculation_ids": [],
                    "value": None,
                }
            ],
            [
                {
                    "evidence_id": "ev-qa",
                    "field": "sec_10k_excerpt_technology",
                }
            ],
            Settings(_env_file=None, llm_model="fixture-reviewer"),
        )
