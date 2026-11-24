import asyncio
import json
from pathlib import Path
from threading import Event, Lock
from time import monotonic

import httpx

from app.modules.research.agents.tools import ToolArgumentsError
from app.modules.research.errors import ModelBudgetError, ModelError, RunCancelledError

PROMPTS = Path(__file__).parent / "prompts"
_REAL_HTTPX_CLIENT = httpx.Client


class CancellationToken:
    """Thread-safe cancellation signal that can also abort an active HTTP call."""

    def __init__(self) -> None:
        self._event = Event()
        self._done = Event()
        self._lock = Lock()
        self._aborts: list = []

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def mark_done(self) -> None:
        self._done.set()

    def wait_done(self, timeout: float = 2.0) -> bool:
        return self._done.wait(timeout)

    def register_abort(self, callback) -> None:
        call_now = False
        with self._lock:
            if self._event.is_set():
                call_now = True
            else:
                self._aborts.append(callback)
        if call_now:
            try:
                callback()
            except Exception:
                pass

    def clear_abort(self, callback) -> None:
        with self._lock:
            self._aborts = [cb for cb in self._aborts if cb is not callback]

    def cancel(self) -> None:
        with self._lock:
            self._event.set()
            callbacks = list(self._aborts)
            self._aborts.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass


async def _post_cancellable(
    url: str,
    headers: dict[str, str],
    payload: dict,
    timeout: float,
    cancel_token: CancellationToken,
) -> httpx.Response:
    """Execute an HTTP POST with an async event loop so cancel_token aborts blocked sockets immediately."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        req_task = asyncio.create_task(client.post(url, headers=headers, json=payload))
        loop = asyncio.get_running_loop()
        cancel_future = loop.create_future()

        def trigger() -> None:
            if not cancel_future.done():
                try:
                    loop.call_soon_threadsafe(cancel_future.set_result, True)
                except RuntimeError:
                    pass

        cancel_token.register_abort(trigger)
        try:
            done, _ = await asyncio.wait(
                {req_task, cancel_future},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancel_future in done:
                req_task.cancel()
                try:
                    await req_task
                except BaseException:
                    pass
                raise RunCancelledError("Research run stopped by user")
            return req_task.result()
        finally:
            cancel_token.clear_abort(trigger)


class ModelClient:
    def __init__(self, settings, cancel_token: CancellationToken | None = None):
        self.settings = settings
        self.cancel_token = cancel_token
        self.deadline = monotonic() + settings.research_run_timeout
        self.calls = 0
        self.tokens = 0
        self.reserved_output_tokens = 0
        self.transmitted_context_bytes = 0
        self.usage = []
        self.response_format_with_tools = True

    def check_deadline(self):
        if self.cancel_token and self.cancel_token.is_cancelled():
            raise RunCancelledError("Research run stopped by user")
        if monotonic() >= self.deadline:
            raise ModelBudgetError("Run wall-clock budget exhausted")

    def complete(self, stage, context, schema, tools):
        """Bounded tool loop. Raw provider errors never enter reports (may contain keys)."""
        if not self.settings.llm_model:
            raise ModelError("LLM_MODEL is not configured")
        messages = [
            {
                "role": "system",
                "content": (PROMPTS / "common.md").read_text()
                + "\n"
                + (PROMPTS / f"{stage}.md").read_text()
                + "\nSchema: "
                + json.dumps(schema),
            },
            {"role": "user", "content": json.dumps(context)},
        ]
        for _ in range(4):
            self.check_deadline()
            remaining = self.settings.llm_run_output_tokens - self.reserved_output_tokens
            remaining_total = self.settings.llm_run_total_tokens - self.tokens
            if self.calls >= 24 or remaining <= 0 or remaining_total <= 0:
                raise ModelBudgetError("Per-run model budget exhausted")
            # UTF-8 bytes conservatively bound text tokens, including tool definitions.
            # Reserve framing room; the provider remains the exact tokenizer authority.
            context_bytes = len(
                json.dumps({"messages": messages, "tools": tools.definitions}).encode("utf-8")
            )
            output_limit = min(self.settings.llm_max_tokens, remaining, remaining_total - context_bytes)
            if output_limit <= 0:
                raise ModelBudgetError("Per-run reported total token budget exhausted")
            if (
                context_bytes + output_limit + 2048 > self.settings.llm_context_window_tokens
                or self.transmitted_context_bytes + context_bytes > self.settings.llm_run_context_bytes
            ):
                raise ModelBudgetError("Serialized model context budget exhausted")
            self.calls += 1
            self.reserved_output_tokens += output_limit
            self.transmitted_context_bytes += context_bytes
            try:
                payload = {
                    "model": self.settings.llm_model,
                    "temperature": 0,
                    "max_tokens": output_limit,
                    "messages": messages,
                    "tools": tools.definitions,
                }
                if self.response_format_with_tools:
                    payload["response_format"] = {"type": "json_object"}
                timeout = min(self.settings.llm_timeout, self.deadline - monotonic())
                url = self.settings.llm_base_url.rstrip("/") + "/chat/completions"
                headers = (
                    {"Authorization": f"Bearer {self.settings.llm_api_key}"}
                    if self.settings.llm_api_key
                    else {}
                )
                if self.cancel_token is not None and httpx.Client is _REAL_HTTPX_CLIENT:
                    response = asyncio.run(
                        _post_cancellable(url, headers, payload, timeout, self.cancel_token)
                    )
                else:
                    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                        response = client.post(url, headers=headers, json=payload)
                if response.status_code == 400 and self.response_format_with_tools:
                    error = response.json().get("error", {})
                    if (
                        isinstance(error, dict)
                        and error.get("message")
                        == "structured response_format with tools/MCP is not supported"
                    ):
                        self.response_format_with_tools = False
                        self.reserved_output_tokens -= output_limit
                        continue
                response.raise_for_status()
                result = response.json()
                self.check_deadline()
                usage = result.get("usage")
                if usage:
                    if not isinstance(usage, dict) or any(
                        not isinstance(value, int) or isinstance(value, bool) or value < 0
                        for key, value in usage.items()
                        if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                    ):
                        raise ModelError("Model returned invalid token usage")
                    self.usage.append(usage)
                    self.tokens += usage.get("total_tokens", 0)
                    if self.tokens > self.settings.llm_run_total_tokens:
                        raise ModelBudgetError("Per-run reported total token budget exhausted")
                    # Reclaim unused output allocation only when the provider reports it.
                    used_output = usage.get("completion_tokens")
                    if isinstance(used_output, int) and 0 <= used_output <= output_limit:
                        self.reserved_output_tokens -= output_limit - used_output
                choice = result["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ModelError(
                        "Model output truncated at output/context limit; return a shorter complete JSON object "
                        "with fewer material claims and only cited IDs."
                    )
                message = choice["message"]
                calls = message.get("tool_calls", [])
                if len(calls) > 8:
                    raise ModelError("Too many tool calls in one response")
                if not calls:
                    return json.loads(message["content"])
                messages.append(message)
                for call in calls:
                    self.check_deadline()
                    try:
                        value = tools.call(
                            call["function"]["name"], json.loads(call["function"]["arguments"])
                        )
                    except ToolArgumentsError:
                        value = {
                            "error": "Tool request rejected. Use a declared tool with exactly empty arguments {}. "
                            "Data is already captured for this run; unavailable data cannot be fetched here."
                        }
                    messages.append(
                        {"role": "tool", "tool_call_id": call["id"], "content": json.dumps(value)}
                    )
            except (httpx.HTTPError, KeyError, IndexError, AttributeError, TypeError, ValueError) as exc:
                if self.cancel_token and self.cancel_token.is_cancelled():
                    raise RunCancelledError("Research run stopped by user") from None
                raise ModelError(f"Model response unavailable or invalid ({type(exc).__name__})") from None
        raise ModelError("Tool iteration budget exhausted")


class FixtureModel:
    """Deterministic test double, never used for live mode."""

    usage = []

    def complete(self, stage, context, schema, tools):
        data = tools.call("get_company_data", {})
        evidence = data["evidence"]
        calculations = tools.call("calculate_metric", {})
        ids = [e["evidence_id"] for e in evidence]
        calc_ids = [c["calculation_id"] for c in calculations]
        claims = []
        if ids:
            claims.append(
                {
                    "text": "Synthetic fixture company evidence is available.",
                    "evidence_ids": [ids[0]],
                    "calculation_ids": [],
                }
            )
        if stage in ("financials", "valuation"):
            for calc in calculations:
                if calc["value"] is not None:
                    claims.append(
                        {
                            "text": calc["metric"].replace("_", " ") + " from deterministic fixture inputs.",
                            "evidence_ids": calc["input_evidence_ids"],
                            "calculation_ids": [calc["calculation_id"]],
                            "value": calc["value"],
                            "unit": calc["unit"],
                            "reference_id": calc["calculation_id"],
                        }
                    )
        result = {
            "stage": stage,
            "summary": f"Synthetic fixture {stage} stage; not live AI analysis.",
            "claims": claims,
            "evidence_ids": ids,
            "calculation_ids": calc_ids,
            "gaps": ["Synthetic test data only; unavailable licensed analyst consensus."],
        }
        extras = {
            "profile": {"identity_check": "Fixture identity only; no live cross-source verification."},
            "financials": {"performance": "Synthetic annual data exercises calculations only."},
            "estimates": {"consensus_available": False},
            "valuation": {"limitations": ["Historical annual EPS is not a current TTM estimate."]},
            "risk": {
                "counterevidence": ["Synthetic inputs cannot establish real company performance."],
                "invalidation_conditions": ["Recheck all findings against live filings."],
                "disputes": [],
            },
            "report": {
                "executive_summary": "Synthetic educational pipeline demonstration; not investment advice."
            },
        }
        return result | extras[stage]
