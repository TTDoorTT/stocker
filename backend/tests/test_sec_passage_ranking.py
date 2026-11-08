"""Offline Phase 3C tests: deterministic, bounded SEC passage ranking."""

import httpx

from app.core.config import Settings
from app.modules.market_data.filing_excerpt import (
    MAX_DOCUMENTS,
    MAX_EXCERPT_CHARS,
    MAX_PASSAGES_PER_TOPIC,
    TOPIC_TERMS,
    extract_passages,
    filing_excerpts,
)
from app.modules.market_data.providers.http import ProviderHTTP
from app.modules.market_data.service import DataService

ROOT = "https://www.sec.gov/Archives/edgar/data"


def _paragraph(subject: str) -> str:
    return (
        f"The company discusses {subject} with detailed operational considerations for its customers "
        "and third-party service partners, including known uncertainties, planning processes, "
        "dependencies, and publicly described business practices."
    )


def _filing(symbol: str, cik: int) -> dict:
    return {
        "symbol": symbol,
        "form": "10-K",
        "filed": "2026-04-01",
        "source_url": f"{ROOT}/{cik}/{cik:010d}26000001/report.htm",
    }


def test_heading_cues_and_topic_ranking_are_unverified():
    html = (
        "<head><script>competition supply chain SECRET-MALICIOUS-SCRIPT</script></head>"
        "<h2>Item 1. Business</h2>"
        f"<p>{_paragraph('artificial intelligence and high bandwidth memory')}</p>"
        f"<p>{_paragraph('manufacturing and supply chain')}</p>"
        "<h2>Item 1A. Risk Factors</h2>"
        f"<p>{_paragraph('competition and customer demand')}</p>"
    )
    matches = extract_passages(html)
    assert {p["topic"] for p in matches} == {"technology", "supply-chain", "competition"}
    assert all(len(p["text"]) <= MAX_EXCERPT_CHARS for p in matches)
    assert all("SECRET-MALICIOUS-SCRIPT" not in p["text"] for p in matches)
    assert all("unverified" in p["section_hint"] for p in matches if p["section_hint"])
    assert any(p["section_hint"] == "Item 1A (unverified heading cue)" for p in matches)
    assert all(p["matched_term"].lower() in TOPIC_TERMS[p["topic"]] for p in matches)


def test_high_value_passages_beat_earlier_low_information_matches():
    early = _paragraph("semiconductor")
    late = _paragraph("artificial intelligence, high bandwidth memory, advanced packaging and semiconductors")
    html = "".join(f"<p>{early} {i}</p>" for i in range(8)) + f"<p>{late}</p>"
    selections = [p for p in extract_passages(html) if p["topic"] == "technology"]
    assert len(selections) <= MAX_PASSAGES_PER_TOPIC
    assert any("high bandwidth memory" in p["text"] for p in selections)
    assert selections[0]["relevance_score"] >= selections[-1]["relevance_score"]


def test_near_duplicate_repeated_paragraphs_are_collapsed_by_topic():
    repeated = _paragraph("semiconductor manufacturing and advanced packaging")
    result = extract_passages("".join(f"<p>{repeated}</p>" for _ in range(10)))
    technology = [p for p in result if p["topic"] == "technology"]
    supply = [p for p in result if p["topic"] == "supply-chain"]
    assert len(technology) == 1
    assert len(supply) == 1


def test_plain_text_and_script_only_inputs_do_not_fabricate_sections():
    text = _paragraph("competition and customer demand")
    selections = extract_passages(text)
    assert selections
    assert all(p["section_hint"] is None for p in selections)
    assert extract_passages(f"<html><script>{text}</script></html>") == []


def test_five_peers_are_balanced_and_retrieval_is_cached(tmp_path):
    peers = [("NVDA", 1045810), ("AMD", 2488), ("INTC", 50863), ("AVGO", 1730168), ("MU", 723125)]
    requests = []
    document = (
        "<h2>Item 1. Business</h2>"
        f"<p>{_paragraph('artificial intelligence and high bandwidth memory')}</p>"
        f"<p>{_paragraph('supply chain and manufacturing')}</p>"
        "<h2>Item 1A. Risk Factors</h2>"
        f"<p>{_paragraph('competition and customer demand')}</p>"
    )

    def handler(req):
        requests.append(str(req.url))
        assert req.headers["user-agent"] == "Stocker QA qa@example.org"
        return httpx.Response(200, text=document, headers={"Content-Type": "text/html"})

    settings = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/test.db",
    )
    data = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(handler))))
    snapshot = {"year": 2025, "mode": "live", "filings": [_filing(s, n) for s, n in peers]}
    response = filing_excerpts(data.sec, snapshot)
    assert len(requests) == MAX_DOCUMENTS == 5
    for topic in ("technology", "supply-chain", "competition"):
        rows = [p for p in response["excerpts"] if p["topic"] == topic]
        assert {p["symbol"] for p in rows} == {symbol for symbol, _ in peers}
        assert [p["symbol"] for p in rows[:5]] == [symbol for symbol, _ in peers]
        assert all(p["relevance_score"] >= 1 for p in rows)
        assert all("unverified" in (p["section_hint"] or "") for p in rows)
    second = filing_excerpts(data.sec, snapshot)
    assert len(requests) == 5
    assert second["excerpts"] and all(p["cached"] is True for p in second["excerpts"])


def test_bad_urls_and_fixture_mode_never_fetch(tmp_path):
    def forbidden(request):
        raise AssertionError("SEC request should not be made")

    settings = Settings(_env_file=None, data_mode="fixtures", database_url=f"sqlite:///{tmp_path}/fix.db")
    data = DataService(settings, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(forbidden))))
    snapshot = {"year": 2025, "mode": "fixtures", "filings": [_filing("NVDA", 1045810)]}
    assert filing_excerpts(data.sec, snapshot)["excerpts"] == []

    live = Settings(
        _env_file=None,
        data_mode="live",
        sec_user_agent="Stocker QA qa@example.org",
        database_url=f"sqlite:///{tmp_path}/live.db",
    )
    data = DataService(live, ProviderHTTP(httpx.Client(transport=httpx.MockTransport(forbidden))))
    unsafe = {
        "year": 2025,
        "mode": "live",
        "filings": [
            {"symbol": "NVDA", "form": "10-K", "filed": "2026-04-01", "source_url": "https://evil.test/a.htm"}
        ],
    }
    assert filing_excerpts(data.sec, unsafe)["excerpts"] == []
