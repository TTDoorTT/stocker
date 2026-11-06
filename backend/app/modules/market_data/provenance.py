import hashlib


def evidence_id(*parts) -> str:
    return "ev-" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]
