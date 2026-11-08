import json

from app.core.config import ROOT
from app.modules.intelligence.industry_profiles import public_capabilities, validate_profiles


class IndustryCatalog:
    def __init__(self):
        self.templates = json.loads((ROOT / "fixtures" / "industries.json").read_text())
        validate_profiles(self.templates)

    def industries(self) -> list[dict]:
        common = [
            "Guided research template, not a verified sector analysis.",
            "Company examples must be verified against current filings; one stock does not represent a sector.",
            "Industry capacity, pricing, market-share and demand datasets are not integrated.",
            "Canadian history/macro support is partial; Canadian company fundamentals remain unavailable.",
        ]
        return [
            dict(template, gaps=common.copy(), **public_capabilities(template["slug"]))
            for template in self.templates
        ]

    def industry(self, slug: str) -> dict:
        for template in self.industries():
            if template["slug"] == slug:
                return template
        raise KeyError("Industry template not found")
