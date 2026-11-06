def render_report(run, outputs):
    sections = {
        "profile": "Company profile",
        "financials": "Financial performance",
        "estimates": "Expectations",
        "valuation": "Valuation",
        "risk": "Risks and counterevidence",
        "report": "Executive summary",
    }
    lines = [
        f"# {run['symbol']} research",
        "",
        f"Mode: {run['mode']} | Status: {run['status']}",
        f"Research captured: {run['started_at']}",
        "",
        "Educational research, not investment advice. No trading recommendations or price targets.",
        "",
    ]
    if run["mode"] == "fixtures":
        lines += ["**SYNTHETIC FIXTURE DATA — deterministic model stub; not live AI research.**", ""]
    for stage in ("report", "profile", "financials", "estimates", "valuation", "risk"):
        lines += [f"## {sections[stage]}", ""]
        output = outputs.get(stage)
        if not output:
            lines += ["Unavailable: this stage did not pass validation.", ""]
            continue
        lines += [output["summary"], ""]
        if stage == "report":
            lines += [output["executive_summary"], ""]
        if stage == "valuation":
            lines += ["- " + text for text in output["limitations"]]
        for claim in output["claims"]:
            refs = claim["evidence_ids"] + claim["calculation_ids"]
            value = "" if claim["value"] is None else f" **{claim['value']:g} {claim['unit']}**"
            lines.append(f"- {claim['text']}{value} ({', '.join(refs)})")
        if stage == "risk":
            lines += ["- " + text for text in output["counterevidence"] + output["invalidation_conditions"]]
        lines.append("")
    lines += [
        "## Deterministic calculations",
        "",
        "| Metric | Value | Unit | References |",
        "|---|---|---|---|",
    ]
    for calc in run["calculations"]:
        value = calc["value"] if calc["value"] is not None else "unavailable: " + str(calc["reason"])
        lines.append(
            f"| {calc['metric']} | {value} | {calc['unit']} | {calc['calculation_id']}; "
            + ", ".join(calc["input_evidence_ids"])
            + " |"
        )
    lines += ["", "## Sources and timestamps", ""]
    for ev in run["evidence"]:
        source = (
            f"[{ev['source_name']}]({ev['source_url']})"
            if ev["source_url"].startswith("https://")
            else f"{ev['source_name']} ({ev['source_url']})"
        )
        lines.append(
            f"- {ev['evidence_id']}: {source} — "
            f"{ev['field']}; fiscal period {ev['period']}; published {ev['published_at'] or 'unavailable'}; "
            f"fetched {ev['fetched_at']}"
        )
    lines += ["", "## Data gaps", ""] + ["- " + gap for gap in sorted(set(run["gaps"]))]
    return "\n".join(lines)
