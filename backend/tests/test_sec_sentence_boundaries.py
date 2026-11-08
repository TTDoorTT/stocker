"""Offline tests for sentence-aware SEC excerpt selection."""

from app.modules.market_data.filing_excerpt import (
    MAX_EXCERPT_CHARS,
    _excerpt,
    extract_passages,
)


def test_no_mid_sentence_truncation():
    preamble = (
        "This filing contains background descriptions of corporate "
        "engineering projects and business conditions that give readers "
        "context about the company's current operations."
    )
    target = (
        "The company describes advanced packaging technologies and "
        "manufacturing partners that support product design and development "
        "across customer deployments and operational needs."
    )

    passages = [p for p in extract_passages(f"<p>{preamble} {target}</p>") if p["topic"] == "technology"]

    assert passages
    assert passages[0]["text"] == target
    assert passages[0]["matched_term"] == "advanced packaging"


def test_preserves_following_risk_caveat():
    text = (
        "The provider discusses advanced packaging. "
        "However, it cannot guarantee supplier capacity and may experience "
        "delays because required components remain subject to "
        "third-party availability."
    )

    result = _excerpt(text, text.index("advanced packaging"))

    assert result == text
    assert "cannot guarantee" in result
    assert "may experience delays" in result


def test_overlong_sentence_is_not_silently_truncated():
    text = (
        "The issuer discusses advanced packaging and "
        + "complex engineering dependencies and technology requirements " * 10
        + "that remain subject to important customer constraints."
    )

    assert len(text) > MAX_EXCERPT_CHARS
    assert _excerpt(text, text.index("advanced packaging")) == ""
    assert extract_passages(f"<p>{text}</p>") == []


def test_alternate_complete_sentence_is_selected():
    overlong = (
        "The issuer describes advanced packaging and "
        + "technology dependencies affecting different deployments " * 10
        + "in its filing."
    )

    other = (
        "The company provides detailed semiconductor engineering disclosures "
        "about manufacturing methods, customer requirements, production "
        "dependencies and operational conditions in its reviewed projects."
    )

    passages = [p for p in extract_passages(f"<p>{overlong} {other}</p>") if p["topic"] == "technology"]

    assert passages
    assert passages[0]["text"] == other
    assert passages[0]["matched_term"] == "semiconductor"


def test_abbreviation_does_not_break_sentence():
    text = (
        "The U.S. company discusses advanced packaging and industry "
        "engineering methods used in semiconductor development, "
        "planning and customer delivery projects. "
        "However, sourcing remains dependent on third parties."
    )

    result = _excerpt(text, text.index("advanced packaging"))

    assert result.startswith("The U.S. company")
    assert result.endswith("parties.")
    assert len(result) <= MAX_EXCERPT_CHARS


def test_unfinished_source_fragment_is_not_used():
    text = (
        "The provider discusses advanced packaging across the deployed "
        "systems and these manufacturing operations without a concluding "
        "disclosure"
    )

    assert extract_passages(text) == []


def test_custom_industry_terms_still_work():
    topics = {
        "technology": ("grid modernization",),
        "supply-chain": ("transformer",),
        "competition": ("competitors",),
    }

    text = (
        "The company discusses grid modernization projects and extensive "
        "technical equipment testing requirements, grid reliability risks "
        "and customer commitments in these disclosures."
    )

    passages = extract_passages(
        f"<p>{text}</p>",
        topic_terms=topics,
    )

    assert any(p["topic"] == "technology" and p["text"] == text for p in passages)
    assert all(len(p["text"]) <= MAX_EXCERPT_CHARS for p in passages)
