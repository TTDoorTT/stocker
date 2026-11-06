import re


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    symbol = symbol.strip().upper()
    prefix = None
    if symbol.startswith(("US:", "CA:")):
        prefix, symbol = symbol.split(":", 1)
    canadian = bool(re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?\.(?:TO|V)", symbol))
    us = bool(re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z])?", symbol)) and not canadian
    actual = "CA" if canadian else "US"
    if not (canadian or us) or (prefix and prefix != actual) or (market is not None and market != actual):
        raise ValueError("Use a U.S. ticker or explicit Canadian .TO (TSX) / .V (TSXV) listing")
    return symbol


def symbol_market(symbol: str) -> str:
    return "CA" if normalize_symbol(symbol).endswith((".TO", ".V")) else "US"
