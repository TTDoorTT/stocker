# Phase 5B.1 — Live QA compatibility

## Scope

- Add optional EXTRA_FRONTEND_ORIGINS for exact loopback HTTP origins.
- Defaults remain localhost:5173 and 127.0.0.1:5173.
- Both CORS and request-origin protection use the same allowlist.
- Align filing claim-review length with the existing 2000-character report schema.
- Preserve all source, citation, verdict and saved-report safeguards.

## Isolated QA configuration

In compose.liveqa.yaml, under services.backend.environment, add:

    EXTRA_FRONTEND_ORIGINS: "http://localhost:5174,http://127.0.0.1:5174"

Do not add this setting to the production environment unless required.

## Limitations

Longer claims are permitted, not encouraged. Model-screened judgments
are not independent verification. This change introduces no database
migration, new API route, external provider, or additional model call.

The website AI settings are unchanged; environment-based configuration
continues to work as before.
