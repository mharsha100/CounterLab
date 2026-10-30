"""A resilient client for NVIDIA Nemotron on Nebius Token Factory.

Retries follow the policy of the official OpenAI SDK: connection errors, timeouts, HTTP 408, 409, 425,
429 and 5xx are retried with exponential backoff and jitter, and the provider's Retry-After header is
honoured. Requests the provider rejects for a reason a retry cannot fix (400, 401, 402, 403, 404, 422)
stop immediately with a fixed code. Every retry is recorded, so the evidence shows exactly how many
requests reached Nebius.

If Token Factory rejects the strict JSON schema (HTTP 400/422), the client falls back once to a relaxed
schema and then to JSON mode with the schema in the instructions. CounterLab validates every response
locally either way, so a weaker provider-side format never weakens the checks.
"""

import copy
import email.utils
import http.client
import json
import random
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

API_BASE = "https://api.tokenfactory.nebius.com/v1/"
RETRYABLE_HTTP = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
SCHEMA_REJECTED_HTTP = frozenset({400, 422})
RELAXED_DROP = frozenset({"pattern", "minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum",
                          "exclusiveMinimum", "exclusiveMaximum", "format", "uniqueItems"})
SCHEMA_MODES = ("strict", "relaxed", "json_object")


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 4            # one request plus up to three retries
    base_seconds: float = 2.0
    cap_seconds: float = 30.0
    max_retry_after: float = 60.0
    max_total_wait: float = 150.0
    max_timeout_retries: int = 1  # a request that timed out may still have been processed


CHAT_POLICY = RetryPolicy()
CATALOG_POLICY = RetryPolicy(attempts=3, base_seconds=1.0, cap_seconds=8.0, max_total_wait=30.0)


class ProviderError(Exception):
    """A provider failure reduced to a fixed code; never carries the provider's message or the key."""

    def __init__(self, code, *, status=None, retryable=False, retry_after=None, kind="http"):
        super().__init__(code)
        self.counterlab_code = code
        self.status, self.retryable, self.retry_after, self.kind = status, retryable, retry_after, kind


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def retry_after_seconds(headers):
    if headers is None:
        return None
    try:
        value = headers.get("retry-after-ms")
        if value is not None:
            return max(0.0, float(value) / 1000)
        value = headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            moment = email.utils.parsedate_to_datetime(value)
            return max(0.0, moment.timestamp() - time.time())
    except (TypeError, ValueError, OverflowError):
        return None


def make_transport(base=API_BASE, timeout=900, catalog_timeout=30):
    """The HTTP transport: one request, no retries, fixed error codes. `base` is overridable for tests.

    A design request may reason and then write a long harness, so chat requests get 15 minutes;
    reading the model catalog gets 30 seconds."""
    chat_timeout = timeout

    def transport(key, route, body=None, *, timeout=None):
        timeout = timeout or (catalog_timeout if route == "models" else chat_timeout)
        headers = {"Authorization": "Bearer " + key, "Accept": "application/json", "User-Agent": "CounterLab/1.0"}
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(base + route, data=data, headers=headers)
        try:
            with urllib.request.build_opener(NoRedirects()).open(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise ProviderError(f"provider_http_{error.code}", status=error.code, retryable=error.code in RETRYABLE_HTTP,
                                retry_after=retry_after_seconds(error.headers)) from None
        except (socket.timeout, TimeoutError):
            raise ProviderError("provider_timeout", retryable=True, kind="timeout") from None
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, OSError):
            raise ProviderError("provider_connection_error", retryable=True, kind="connection") from None
        try:
            return json.loads(raw)
        except ValueError:
            raise ProviderError("provider_response_invalid", retryable=True, kind="response") from None
    return transport


request = make_transport()


def classify(error):
    """Return a ProviderError describing `error`, or None when it is not a provider failure."""
    if isinstance(error, ProviderError):
        return error
    if isinstance(error, urllib.error.HTTPError):
        return ProviderError(f"provider_http_{error.code}", status=error.code, retryable=error.code in RETRYABLE_HTTP,
                             retry_after=retry_after_seconds(error.headers))
    if isinstance(error, (socket.timeout, TimeoutError)):
        return ProviderError("provider_timeout", retryable=True, kind="timeout")
    code = getattr(error, "counterlab_code", None)
    if isinstance(code, str) and code.startswith("provider_"):
        return ProviderError(code, retryable=code in ("provider_connection_error", "provider_timeout"), kind="connection")
    if isinstance(error, (urllib.error.URLError, http.client.HTTPException, ConnectionError)):
        return ProviderError("provider_connection_error", retryable=True, kind="connection")
    return None


def relax_schema(schema):
    if isinstance(schema, dict):
        return {key: relax_schema(value) for key, value in schema.items() if key not in RELAXED_DROP}
    if isinstance(schema, list):
        return [relax_schema(item) for item in schema]
    return schema


def adapt(body, mode):
    """The same request in a response-format mode the provider accepts."""
    response_format = body.get("response_format") or {}
    if mode == "strict" or response_format.get("type") != "json_schema":
        return body
    adapted = copy.deepcopy(body)
    schema = response_format["json_schema"]["schema"]
    if mode == "relaxed":
        adapted["response_format"]["json_schema"]["schema"] = relax_schema(schema)
        return adapted
    adapted["response_format"] = {"type": "json_object"}
    instruction = ("\n\nReturn exactly one JSON object, with no prose and no code fences, that matches this JSON "
                   "Schema:\n" + json.dumps(relax_schema(schema), ensure_ascii=False))
    messages = adapted["messages"]
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = str(messages[0].get("content", "")) + instruction
    else:
        messages.insert(0, {"role": "system", "content": instruction.strip()})
    return adapted


def utc_stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ResilientClient:
    """Bounded retries and response-format fallback around a single-request transport."""

    def __init__(self, transport, key, *, wait=None, notify=None, events=None, chat_policy=CHAT_POLICY,
                 catalog_policy=CATALOG_POLICY, rng=random.random, schema_mode="strict"):
        self.transport, self.key = transport, key
        self.wait = wait or (lambda seconds: time.sleep(seconds) or False)
        self.notify = notify or (lambda message: None)
        self.events = events if events is not None else []
        self.chat_policy, self.catalog_policy, self.rng = chat_policy, catalog_policy, rng
        self.schema_mode = schema_mode
        self.requests_sent = 0

    def _delay(self, policy, attempt, error):
        backoff = min(policy.cap_seconds, policy.base_seconds * 2 ** (attempt - 1))
        backoff *= 1 - 0.25 * self.rng()
        if error.retry_after is not None:
            return min(policy.max_retry_after, max(error.retry_after, 0.5))
        return backoff

    def _send(self, route, body, policy, purpose):
        waited, timeouts = 0.0, 0
        for attempt in range(1, policy.attempts + 1):
            try:
                self.requests_sent += 1
                return self.transport(self.key, route, body)
            except Exception as raw:  # noqa: BLE001 - classified below, everything else propagates
                error = classify(raw)
                if error is None:
                    raise
                if error.kind == "timeout":
                    timeouts += 1
                delay = self._delay(policy, attempt, error)
                give_up = (not error.retryable or attempt == policy.attempts or waited + delay > policy.max_total_wait
                           or (error.kind == "timeout" and timeouts > policy.max_timeout_retries))
                if give_up:
                    raise error from None
                waited += delay
                self.events.append({"at": utc_stamp(), "kind": "retry", "purpose": purpose, "attempt": attempt,
                                    "code": error.counterlab_code, "delay_seconds": round(delay, 2)})
                reason = (f"HTTP {error.status}" if error.status else
                          {"timeout": "the request timed out", "connection": "the connection dropped",
                           "response": "an unreadable response"}.get(error.kind, "a temporary error"))
                self.notify(f"Nebius returned {reason}; retrying in {max(1, round(delay))} s "
                            f"(attempt {attempt + 1} of {policy.attempts})")
                if self.wait(delay):
                    from counterlab.open_lab.control import InvestigationCancelled
                    raise InvestigationCancelled()
        raise ProviderError("provider_retry_limit_reached")  # unreachable; loop always returns or raises

    def catalog(self):
        payload = self._send("models", None, self.catalog_policy, "catalog")
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        return sorted({row["id"] for row in rows if isinstance(row, dict) and isinstance(row.get("id"), str)})

    def chat(self, body, purpose="chat"):
        while True:
            prepared = adapt(body, self.schema_mode)
            try:
                return self._send("chat/completions", prepared, self.chat_policy, purpose)
            except ProviderError as error:
                structured = (body.get("response_format") or {}).get("type") == "json_schema"
                if structured and error.status in SCHEMA_REJECTED_HTTP and self.schema_mode != "json_object":
                    following = SCHEMA_MODES[SCHEMA_MODES.index(self.schema_mode) + 1]
                    self.events.append({"at": utc_stamp(), "kind": "response_format_fallback", "purpose": purpose,
                                        "status": error.status, "from": self.schema_mode, "to": following})
                    self.notify(f"Nebius rejected the strict response format (HTTP {error.status}); "
                                f"retrying with {following.replace('_', ' ')} output")
                    self.schema_mode = following
                    continue
                raise


NEMOTRON_ORDER = ("ultra", "super", "nano")


def choose_model(available, preferred):
    """Pick the configured Nemotron model, or the strongest Nemotron model the account can use."""
    ids = list(available)
    if preferred in ids:
        return preferred, None
    by_lower = {item.lower(): item for item in ids}
    if preferred and preferred.lower() in by_lower:
        return by_lower[preferred.lower()], None
    nemotron = [item for item in ids if "nemotron" in item.lower()]
    if not nemotron:
        return None, "no_nemotron_model_in_catalog"

    def rank(model):
        lowered = model.lower()
        size = next((index for index, name in enumerate(NEMOTRON_ORDER) if name in lowered), len(NEMOTRON_ORDER))
        return (size, "vl" in lowered.split("-"), "embed" in lowered or "rerank" in lowered or "guard" in lowered, model)

    candidates = [item for item in nemotron if not any(word in item.lower() for word in ("embed", "rerank", "guard", "reward"))]
    return (sorted(candidates or nemotron, key=rank)[0], "preferred_model_unavailable")


def check_connection(client, preferred):
    """Read the model catalog (no inference, no credits) and report whether Nemotron is usable."""
    started = time.monotonic()
    result = {"checked_at": utc_stamp(), "preferred_model": preferred}
    try:
        ids = client.catalog()
    except ProviderError as error:
        return {**result, "ok": False, "error": error.counterlab_code,
                "latency_ms": round(1000 * (time.monotonic() - started))}
    model, note = choose_model(ids, preferred)
    return {**result, "ok": model is not None, "latency_ms": round(1000 * (time.monotonic() - started)),
            "model": model, "model_note": note, "error": None if model else "no_nemotron_model_in_catalog",
            "nemotron_models": [item for item in ids if "nemotron" in item.lower()][:40]}


PROBE_SCHEMA = {"type": "object", "properties": {"status": {"type": "string", "enum": ["ready"]},
                                                  "model_family": {"type": "string"}},
                "required": ["status", "model_family"], "additionalProperties": False}


def probe(client, model, *, max_tokens=2048):
    """One small structured request: proves the key, the model and JSON output work end to end."""
    started = time.monotonic()
    body = {"model": model, "stream": False, "max_tokens": max_tokens, "temperature": 1.0, "top_p": 0.95,
            "messages": [{"role": "system", "content": "You are a connectivity check. Answer briefly."},
                         {"role": "user", "content": 'Reply with {"status": "ready", "model_family": "<your model family>"}.'}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "counterlab_probe", "strict": True,
                                                                       "schema": PROBE_SCHEMA}}}
    result = {"checked_at": utc_stamp(), "model": model}
    try:
        payload = client.chat(body, purpose="probe")
    except ProviderError as error:
        return {**result, "ok": False, "error": error.counterlab_code,
                "latency_ms": round(1000 * (time.monotonic() - started))}
    choice = (payload.get("choices") or [{}])[0] if isinstance(payload, dict) else {}
    content = (choice.get("message") or {}).get("content")
    usage = payload.get("usage") if isinstance(payload, dict) and isinstance(payload.get("usage"), dict) else {}
    try:
        from counterlab.open_lab.planner import extract_json
        answer = extract_json(content)
        ok = answer.get("status") == "ready"
    except Exception:  # noqa: BLE001 - any parse failure is reported as a fixed code
        ok = False
    returned = payload.get("model") if isinstance(payload, dict) else None
    error = (None if ok and (returned or "").lower() == model.lower() else
             "returned_model_mismatch" if ok else
             "output_allowance_exhausted" if choice.get("finish_reason") == "length" else "probe_response_invalid")
    return {**result, "ok": error is None, "error": error, "returned_model": returned,
            "latency_ms": round(1000 * (time.monotonic() - started)), "schema_mode": client.schema_mode,
            "usage": {key: value for key, value in usage.items()
                      if key in ("prompt_tokens", "completion_tokens", "total_tokens") and type(value) is int}}
