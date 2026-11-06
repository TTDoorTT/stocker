"""Bounded authenticated model discovery; never prints endpoint/auth/response body.

Native: PYTHONPATH=backend backend/.venv/bin/python scripts/model_connectivity.py
Compose: docker compose run --rm --no-deps -T backend python /workspace/scripts/model_connectivity.py
"""

import json
import sys

import httpx

from app.core.config import Settings
from app.modules.research.configuration.service import AIConfiguration


def main():
    try:
        settings = AIConfiguration(Settings()).current()
        response = httpx.get(
            settings.llm_base_url.rstrip("/") + "/models",
            headers={"Authorization": "Bearer " + settings.llm_api_key},
            timeout=10,
        )
        listed = response.status_code == 200 and any(
            row.get("id") == settings.llm_model for row in response.json().get("data", [])
        )
        print(json.dumps({"http_status": response.status_code, "configured_model_listed": listed}))
        return 0 if listed else 1
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
