"""Deterministic Markdown report rendering from validated six-stage research outputs."""

from __future__ import annotations

from math import isfinite

METRIC_LABELS = {
    "revenue_yoy": "Revenue YoY Growth",
    "eps_growth": "Annual EPS YoY Growth",
    "operating_margin": "Operating Margin",
    "profit_margin": "Net Profit Margin",
    "free_cash_flow": "Free Cash Flow",
    "current_ratio": "Current Ratio",
    "debt_to_equity": "Long-Term Debt / Equity",
    "interest_coverage": "Interest Coverage",
    "pe_annual": "P/E Ratio (Annual EPS)",
    "daily_return": "Daily Return",
    "price_history_return": "Trailing Price Return",
    "ttm_revenue": "TTM Revenue",
    "ttm_net_income": "TTM Net Income",
    "ttm_gross_profit": "TTM Gross Profit",
    "ttm_operating_cash_flow": "TTM Operating Cash Flow",
}

HEADLINE_METRICS = (
    "revenue_yoy",
    "operating_margin",
    "profit_margin",
    "free_cash_flow",
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "pe_annual",
    "price_history_return",
)

_CRITICAL_SYSTEM_GAP_MARKERS = (
    "Unresolved risk disputes",
    "exhausted bounded validation attempts",
    "stopped by the user",
    "Price history unavailable",
)


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def _ref_link(ref_id: str) -> str:
    clean = _escape_cell(ref_id)
    return f"[{clean}](#ref-{clean})"


def _format_currency(value: float, currency: str) -> str:
    prefix = "CA$" if currency == "CAD" else "$"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1e12:
        return f"{sign}{prefix}{magnitude / 1e12:,.2f}T"
    if magnitude >= 1e9:
        return f"{sign}{prefix}{magnitude / 1e9:,.2f}B"
    if magnitude >= 1e6:
        return f"{sign}{prefix}{magnitude / 1e6:,.2f}M"
    if magnitude >= 1e3:
        return f"{sign}{prefix}{magnitude / 1e3:,.2f}K"
    return f"{sign}{prefix}{magnitude:,.2f}"


def format_numeric_value(value: float | None, unit: str | None) -> str:
    if value is None or not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
        return "Unavailable"
    unit_text = (unit or "").strip()
    if unit_text in {"USD", "CAD"}:
        return _format_currency(float(value), unit_text)
    if unit_text == "%":
        return f"{float(value):.2f}%"
    if unit_text == "ratio":
        return f"{float(value):.2f}x"
    if unit_text in {"USD/shares", "CAD/shares"}:
        prefix = "CA$" if unit_text.startswith("CAD") else "$"
        sign = "-" if value < 0 else ""
        return f"{sign}{prefix}{abs(float(value)):,.2f}/share"
    formatted = f"{float(value):,.2f}" if abs(value) >= 1 else f"{float(value):.4g}"
    return f"{formatted} {unit_text}".strip()


def _render_claims(claims: list[dict]) -> list[str]:
    lines: list[str] = []
    for claim in claims:
        refs = claim["evidence_ids"] + claim["calculation_ids"]
        ref_part = f" ({', '.join(_ref_link(ref) for ref in refs)})" if refs else ""
        if claim["value"] is None:
            lines.append(f"- {claim['text']}{ref_part}")
        else:
            formatted = format_numeric_value(claim["value"], claim["unit"])
            lines.append(f"- **{formatted}** — {claim['text']}{ref_part}")
    return lines


def _render_key_metrics(calculations: list[dict]) -> list[str]:
    available = [calc for calc in calculations if calc.get("value") is not None]
    if not available:
        return []
    by_metric = {calc["metric"]: calc for calc in available}
    selected = [by_metric[metric] for metric in HEADLINE_METRICS if metric in by_metric]
    if not selected:
        selected = available[:8]
    lines = [
        "### Key metrics snapshot",
        "",
        "| Metric | Value | Reference |",
        "|---|---|---|",
    ]
    for calc in selected:
        label = _escape_cell(_metric_label(calc["metric"]))
        formatted = _escape_cell(format_numeric_value(calc["value"], calc["unit"]))
        lines.append(f"| {label} | **{formatted}** | {_ref_link(calc['calculation_id'])} |")
    lines.append("")
    return lines


def _select_report_gaps(run: dict, outputs: dict) -> list[str]:
    """Use the curated report-stage gaps plus critical system gaps to avoid 30-bullet repetition."""
    report_output = outputs.get("report")
    if report_output and report_output.get("gaps"):
        selected = list(dict.fromkeys(report_output["gaps"]))
        for gap in run.get("gaps", []):
            if any(marker in gap for marker in _CRITICAL_SYSTEM_GAP_MARKERS) and gap not in selected:
                selected.append(gap)
        return selected
    return sorted(set(run.get("gaps", [])))


def render_report(run, outputs):
    sections = {
        "profile": "Company profile",
        "financials": "Financial performance",
        "estimates": "Expectations",
        "valuation": "Valuation",
        "risk": "Risks and counterevidence",
        "report": "Executive summary",
    }
    is_quick = run.get("strategy") == "single"
    depth_label = "Quick (1-pass synthesis)" if is_quick else "Deep (6-stage specialist)"
    title_label = "Quick Research Brief" if is_quick else "Research Brief"
    lines = [
        f"# {run['symbol']} — {title_label}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| **Symbol** | `{_escape_cell(run['symbol'])}` ({_escape_cell(run.get('market', 'US'))}) |",
        f"| **Depth** | {depth_label} |",
        f"| **Mode** | `{_escape_cell(run['mode'])}` |",
        f"| **Status** | `{_escape_cell(run['status'])}` |",
        f"| **Model** | `{_escape_cell(run.get('model_id', 'unknown'))}` |",
        f"| **Captured** | `{_escape_cell(run['started_at'])}` |",
        "",
        "> Educational research only — not investment advice. No trading recommendations or price targets.",
        "",
    ]
    if run["mode"] == "fixtures":
        lines += [
            "> **SYNTHETIC FIXTURE DATA — deterministic model stub; not live AI research.**",
            "",
        ]

    rendered_stages = (
        ("report",) if is_quick else ("report", "profile", "financials", "estimates", "valuation", "risk")
    )
    for stage in rendered_stages:
        lines += [f"## {sections[stage]}", ""]
        output = outputs.get(stage)
        if not output:
            lines += ["Unavailable: this stage did not pass validation.", ""]
            continue

        if stage == "report":
            lines += [f"> **Bottom line:** {output['executive_summary']}", ""]
            if output["claims"]:
                lines += _render_claims(output["claims"])
                lines.append("")
            if output["summary"] and output["summary"].strip() != output["executive_summary"].strip():
                lines += [f"**Coverage & completeness:** {output['summary']}", ""]
            lines += _render_key_metrics(run.get("calculations", []))
            continue

        lines += [output["summary"], ""]

        if stage == "profile" and output.get("identity_check"):
            lines += ["### Identity verification", "", output["identity_check"], ""]

        if stage == "financials" and output.get("performance"):
            lines += ["### Performance overview", "", output["performance"], ""]

        if stage == "estimates":
            consensus_label = (
                "Available"
                if output.get("consensus_available")
                else "Unavailable (no licensed analyst consensus provider integrated)"
            )
            lines += [f"**Licensed analyst consensus:** {consensus_label}", ""]

        if output["claims"]:
            lines += _render_claims(output["claims"])
            lines.append("")

        if stage == "valuation" and output.get("limitations"):
            lines += ["### Valuation limitations", ""]
            lines += [f"- {text}" for text in output["limitations"]]
            lines.append("")

        if stage == "risk":
            if output.get("counterevidence"):
                lines += ["### Counterevidence", ""]
                lines += [f"- {text}" for text in output["counterevidence"]]
                lines.append("")
            if output.get("invalidation_conditions"):
                lines += ["### Invalidation conditions", ""]
                lines += [f"- {text}" for text in output["invalidation_conditions"]]
                lines.append("")

    lines += [
        "## Deterministic calculations",
        "",
        "| Metric | Value | Unit | References |",
        "|---|---|---|---|",
    ]
    for calc in run["calculations"]:
        label = _escape_cell(_metric_label(calc["metric"]))
        value = (
            format_numeric_value(calc["value"], calc["unit"])
            if calc["value"] is not None
            else f"Unavailable ({calc['reason']})"
        )
        refs = "; ".join(
            [f"`{_escape_cell(calc['calculation_id'])}`"]
            + [_ref_link(ref) for ref in calc["input_evidence_ids"]]
        )
        lines.append(f"| {label} | {_escape_cell(value)} | {_escape_cell(calc['unit'])} | {refs} |")

    lines += ["", "## Data gaps", ""]
    gaps = _select_report_gaps(run, outputs)
    if gaps:
        lines += [f"- {gap}" for gap in gaps]
    else:
        lines.append("- None recorded.")

    lines += [
        "",
        "## Sources and timestamps",
        "",
        "| Evidence ID | Field | Period | Source | Published | Fetched |",
        "|---|---|---|---|---|---|",
    ]
    for ev in run["evidence"]:
        source = (
            f"[{_escape_cell(ev['source_name'])}]({ev['source_url']})"
            if str(ev["source_url"]).startswith("https://")
            else f"{_escape_cell(ev['source_name'])} ({_escape_cell(ev['source_url'])})"
        )
        lines.append(
            f"| `{_escape_cell(ev['evidence_id'])}` | {_escape_cell(ev['field'])} | "
            f"{_escape_cell(ev['period'])} | {source} | "
            f"{_escape_cell(ev['published_at'] or 'Unavailable')} | `{_escape_cell(ev['fetched_at'])}` |"
        )
    return "\n".join(lines)
