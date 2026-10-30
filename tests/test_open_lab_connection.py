"""The Nemotron connection, settings, Stop and Run again. Offline: a local fake Token Factory stands in for Nebius."""
import http.server
import json
import socket
import threading
import time
import unittest
import urllib.error
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from counterlab.api import create_app
from counterlab.investigator import MODELS
from counterlab.open_lab.control import InvestigationCancelled
from counterlab.open_lab.planner import ModelTurnError, extract_json
from counterlab.open_lab.provider import (ProviderError, ResilientClient, RetryPolicy, adapt, choose_model,
                                          make_transport, retry_after_seconds)
from counterlab.open_lab.sandbox import LocalProcessSandbox
from counterlab.open_lab.settings import read_env
from counterlab.open_lab.simulated import simulated_transport
try:  # discovered from tests/ (the documented command) or imported as a package module
    from test_open_lab import HEADERS, Scratch
except ImportError:  # pragma: no cover
    from tests.test_open_lab import HEADERS, Scratch

FAST = RetryPolicy(attempts=4, base_seconds=0.01, cap_seconds=0.02, max_retry_after=0.05, max_total_wait=5)
ACTION = {"Content-Type": "application/json"}


class FakeTokenFactory:
    """A local OpenAI-compatible server that replays a scripted list of responses."""

    def __init__(self):
        self.script, self.requests = [], []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def respond(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                owner.requests.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
                step = owner.script.pop(0) if owner.script else ("ok",)
                kind = step[0]
                if kind == "drop":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                if kind == "sleep":
                    time.sleep(step[1])
                    return
                if kind == "status":
                    status, headers = step[1], step[2] if len(step) > 2 else {}
                    data = json.dumps({"error": {"message": "secret provider detail"}}).encode()
                    self.send_response(status)
                    for name, value in headers.items():
                        self.send_header(name, value)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if kind == "reject_schema" and body and body.get("response_format", {}).get("type") == "json_schema":
                    return self.send_status(400)
                if body and body.get("response_format", {}).get("type") == "json_object":
                    payload = {"model": body["model"], "choices": [{"finish_reason": "stop", "message": {
                        "content": json.dumps({"status": "ready", "model_family": "test"})}}]}
                else:
                    payload = simulated_transport("k", "models" if self.path.endswith("/models") else "chat/completions", body)
                if body and body.get("model"):
                    payload["model"] = body["model"]
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def send_status(self, status):
                data = b"{}"
                self.send_response(status)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = respond

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}/v1/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def probe_body():
    return {"model": MODELS[0], "max_tokens": 64, "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "counterlab_probe", "strict": True, "schema": {
                "type": "object", "properties": {"status": {"type": "string", "pattern": "^r", "maxLength": 9}},
                "required": ["status"], "additionalProperties": False}}}}


class ResilientClientTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeTokenFactory()
        self.addCleanup(self.fake.close)
        self.waits = []
        self.client = ResilientClient(make_transport(self.fake.base, timeout=2), "test-key", chat_policy=FAST,
                                      catalog_policy=FAST, wait=lambda seconds: self.waits.append(seconds) or False)

    def test_rate_limits_and_server_errors_are_retried_then_succeed(self):
        self.fake.script = [("status", 429, {"Retry-After": "0"}), ("status", 503), ("ok",)]
        payload = self.client.chat(probe_body())
        self.assertEqual(payload["model"], MODELS[0])
        self.assertEqual(len(self.fake.requests), 3)
        self.assertEqual([event["code"] for event in self.client.events], ["provider_http_429", "provider_http_503"])
        self.assertEqual(len(self.waits), 2)
        self.assertTrue(all(request["auth"] == "Bearer test-key" for request in self.fake.requests))

    def test_errors_a_retry_cannot_fix_stop_immediately(self):
        for status in (401, 402, 403, 404):
            self.fake.requests.clear()
            self.fake.script = [("status", status)]
            with self.assertRaises(ProviderError) as caught:
                self.client.catalog()
            self.assertEqual(caught.exception.counterlab_code, f"provider_http_{status}")
            self.assertEqual(len(self.fake.requests), 1)
            self.assertNotIn("secret provider detail", str(caught.exception))

    def test_persistent_outage_gives_up_after_the_policy_limit(self):
        self.fake.script = [("status", 503)] * 10
        with self.assertRaises(ProviderError) as caught:
            self.client.chat(probe_body())
        self.assertEqual(caught.exception.counterlab_code, "provider_http_503")
        self.assertEqual(len(self.fake.requests), FAST.attempts)

    def test_dropped_connections_are_retried(self):
        self.fake.script = [("drop",), ("ok",)]
        self.assertIn("data", {"data": self.client.catalog()})
        self.assertEqual(self.client.events[0]["code"], "provider_connection_error")

    def test_a_timed_out_request_is_retried_only_once(self):
        client = ResilientClient(make_transport(self.fake.base, timeout=0.3), "k", chat_policy=FAST, wait=lambda s: False)
        self.fake.script = [("sleep", 1.0), ("sleep", 1.0), ("ok",)]
        with self.assertRaises(ProviderError) as caught:
            client.chat(probe_body())
        self.assertEqual(caught.exception.counterlab_code, "provider_timeout")
        self.assertEqual(len(self.fake.requests), 2)

    def test_a_rejected_strict_schema_falls_back_and_is_recorded(self):
        self.fake.script = [("reject_schema",), ("reject_schema",), ("reject_schema",)]
        payload = self.client.chat(probe_body())
        self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
        formats = [request["body"]["response_format"] for request in self.fake.requests]
        self.assertEqual([item["type"] for item in formats], ["json_schema", "json_schema", "json_object"])
        self.assertNotIn("pattern", json.dumps(formats[1]))
        self.assertIn("matches this JSON Schema", self.fake.requests[-1]["body"]["messages"][0]["content"])
        self.assertEqual(self.client.schema_mode, "json_object")
        self.assertEqual([e["to"] for e in self.client.events if e["kind"] == "response_format_fallback"], ["relaxed", "json_object"])

    def test_cancel_during_backoff_stops_the_retry(self):
        client = ResilientClient(make_transport(self.fake.base, timeout=2), "k", chat_policy=FAST, wait=lambda s: True)
        self.fake.script = [("status", 503)]
        with self.assertRaises(InvestigationCancelled):
            client.chat(probe_body())


class ProviderHelperTests(unittest.TestCase):
    def test_retry_after_forms(self):
        self.assertEqual(retry_after_seconds({"Retry-After": "7"}), 7.0)
        self.assertEqual(retry_after_seconds({"retry-after-ms": "1500"}), 1.5)
        self.assertIsNone(retry_after_seconds({}))
        future = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 30))
        self.assertTrue(20 <= retry_after_seconds({"Retry-After": future}) <= 31)

    def test_model_choice_prefers_the_configured_then_strongest_nemotron(self):
        self.assertEqual(choose_model([MODELS[0], "other/x"], MODELS[0]), (MODELS[0], None))
        self.assertEqual(choose_model([MODELS[0].lower()], MODELS[0]), (MODELS[0].lower(), None))
        self.assertEqual(choose_model(["nvidia/Nemotron-Nano-9B", "nvidia/Nemotron-3-Super-120b-a12b", "nvidia/nemotron-embed"], MODELS[0]),
                         ("nvidia/Nemotron-3-Super-120b-a12b", "preferred_model_unavailable"))
        self.assertEqual(choose_model(["meta/llama"], MODELS[0]), (None, "no_nemotron_model_in_catalog"))

    def test_json_mode_keeps_the_schema_in_the_instructions(self):
        adapted = adapt(probe_body(), "json_object")
        self.assertEqual(adapted["response_format"], {"type": "json_object"})
        self.assertIn('"status"', adapted["messages"][0]["content"])
        self.assertEqual(adapt(probe_body(), "strict"), probe_body())

    def test_model_output_is_parsed_through_reasoning_fences_and_prose(self):
        self.assertEqual(extract_json('<think>long reasoning {"no": 1}</think>\n{"a": 1}'), {"a": 1})
        self.assertEqual(extract_json('```json\n{"a": 2}\n```'), {"a": 2})
        self.assertEqual(extract_json('Here is the plan:\n{"a": 3}\nThanks.'), {"a": 3})
        with self.assertRaises(ModelTurnError):
            extract_json("no json here")


class ExampleFileTests(Scratch):
    def test_example_listing_skips_caches_and_compiled_files(self):
        from counterlab.open_lab.service import example_paths
        (self.directory / "pkg" / "__pycache__").mkdir(parents=True)
        (self.directory / "pkg" / "algo.py").write_text("x = 1\n")
        (self.directory / "pkg" / "__pycache__" / "algo.cpython-313.pyc").write_bytes(b"\x00")
        (self.directory / "pkg" / ".hidden").write_text("no")
        self.assertEqual([path.name for path in example_paths(self.directory)], ["algo.py"])


class ServiceTests(Scratch):
    def make(self, transport=simulated_transport, read_only=False, key="open-lab-test-secret-0123456789"):
        env = self.directory / f"env-{uuid.uuid4().hex[:6]}"
        env.write_text("# local settings\nOTHER_SETTING=keep-me\n" + (f"NEBIUS_API_KEY={key}\n" if key else ""), encoding="utf-8")

        def configure():
            values = read_env(env)
            if not values.get("NEBIUS_API_KEY"):
                raise ValueError("missing")
            return values
        name = uuid.uuid4().hex[:8]
        app = create_app(state_root=self.directory / f"state-{name}", run_root=self.directory / f"runs-{name}", serve_frontend=False,
                         transport=transport, configure=configure, read_only=read_only, open_sandbox=LocalProcessSandbox(), env_path=env)
        app.state.open_lab.chat_policy = app.state.open_lab.catalog_policy = FAST
        client = TestClient(app).__enter__()
        self.addCleanup(lambda: (client.__exit__(None, None, None), app.state.workspace.executor.shutdown(wait=True)))
        return app, client, env

    def start(self, app, client, **changes):
        payload = {"request_id": uuid.uuid4().hex, "confirm_credit_use": True, "question": "Are both reservoir samplers uniform?",
                   "example_id": "reservoir-samplers", **changes}
        with patch.object(app.state.workspace.executor, "submit") as submit:
            response = client.post("/api/open-investigations", headers=HEADERS, json=payload)
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()["id"], submit.call_args.args[1:]

    def test_saving_a_key_never_echoes_it_and_keeps_other_settings(self):
        app, client, env = self.make(key=None)
        self.assertFalse(client.get("/api/settings").json()["connection"]["key_configured"])
        headers = {**ACTION, "X-CounterLab-Action": "save-settings"}
        self.assertEqual(client.post("/api/settings/api-key", json={"api_key": "abc"}, headers=headers).status_code, 422)
        self.assertEqual(client.post("/api/settings/api-key", json={"api_key": "valid-looking-key-0123456789\nEVIL=1"},
                                     headers=headers).status_code, 422)
        self.assertEqual(client.post("/api/settings/api-key", json={"api_key": "valid-looking-key-0123456789"}).status_code, 403)
        response = client.post("/api/settings/api-key", json={"api_key": "Bearer v1.secret-key-0123456789abcdef"}, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("secret-key-0123456789abcdef", response.text)
        self.assertTrue(response.json()["connection"]["key_configured"])
        self.assertTrue(response.json()["check"]["ok"])
        text = env.read_text()
        self.assertIn("OTHER_SETTING=keep-me", text)
        self.assertIn("NEBIUS_API_KEY=v1.secret-key-0123456789abcdef", text)
        self.assertNotIn("EVIL", text)
        for path in ("/api/settings", "/api/open-lab"):
            self.assertNotIn("secret-key-0123456789abcdef", client.get(path).text)
        model = client.post("/api/settings/model", json={"model": "meta/llama-3"}, headers=headers)
        self.assertEqual(model.status_code, 422)
        self.assertEqual(client.post("/api/settings/model", json={"model": "nvidia/Nemotron-3-Super-120b-a12b"}, headers=headers).status_code, 200)
        self.assertEqual(client.get("/api/open-lab").json()["model"], "nvidia/Nemotron-3-Super-120b-a12b")

    def test_read_only_mode_cannot_change_settings(self):
        _, client, _ = self.make(read_only=True)
        headers = {**ACTION, "X-CounterLab-Action": "save-settings"}
        self.assertEqual(client.post("/api/settings/api-key", json={"api_key": "valid-looking-key-0123456789"}, headers=headers).status_code, 403)
        self.assertEqual(client.post("/api/connection/check", json={}, headers={**ACTION, "X-CounterLab-Action": "check-connection"}).status_code, 403)

    def test_connection_check_and_test_request(self):
        calls = []

        def transport(key, route, body=None):
            calls.append(route)
            return simulated_transport(key, route, body)
        _, client, _ = self.make(transport)
        headers = {**ACTION, "X-CounterLab-Action": "check-connection"}
        check = client.post("/api/connection/check", json={}, headers=headers).json()
        self.assertEqual((check["ok"], check["model"]), (True, MODELS[0]))
        self.assertEqual(calls, ["models"])
        self.assertEqual(client.post("/api/connection/probe", json={}, headers=headers).status_code, 422)
        probed = client.post("/api/connection/probe", json={"confirm_credit_use": True}, headers=headers).json()
        self.assertTrue(probed["probe"]["ok"], probed)
        self.assertEqual(probed["probe"]["schema_mode"], "strict")
        self.assertEqual(calls, ["models", "chat/completions"])
        contract = client.get("/api/open-lab").json()
        self.assertTrue(contract["connection"]["last_check"]["probe"]["ok"])
        self.assertNotIn("open-lab-test-secret", json.dumps(contract))

    def test_transient_provider_errors_during_a_run_are_retried_and_recorded(self):
        failures = {"chat": 2}

        def flaky(key, route, body=None):
            if route == "chat/completions" and failures["chat"]:
                failures["chat"] -= 1
                raise urllib.error.HTTPError("https://api.tokenfactory.nebius.com/v1/chat/completions", 503, "busy", {}, None)
            return simulated_transport(key, route, body)
        app, client, _ = self.make(flaky)
        run_id, args = self.start(app, client)
        app.state.open_lab.work(*args)
        record = client.get(f"/api/open-investigations/{run_id}").json()
        self.assertEqual(record["state"], "completed", record.get("error"))
        self.assertEqual(record["summary"]["automatic_retries"], 2)
        self.assertEqual(record["summary"]["provider_requests"], record["summary"]["model_calls"] + 2 + 1)
        self.assertEqual([e["code"] for e in record["summary"]["provider_events"]], ["provider_http_503"] * 2)
        self.assertEqual(record["verification"]["evaluations_recomputed"], 2)

    def test_the_strongest_available_nemotron_is_used_when_the_preferred_one_is_missing(self):
        def catalog_without_ultra(key, route, body=None):
            if route == "models":
                return {"data": [{"id": "nvidia/Nemotron-3-Super-120b-a12b"}, {"id": "meta/llama"}]}
            payload = simulated_transport(key, route, body)
            payload["model"] = body["model"]
            return payload
        app, client, _ = self.make(catalog_without_ultra)
        run_id, args = self.start(app, client)
        app.state.open_lab.work(*args)
        record = client.get(f"/api/open-investigations/{run_id}").json()
        self.assertEqual(record["state"], "completed")
        self.assertEqual(record["connection"]["model"], "nvidia/Nemotron-3-Super-120b-a12b")
        self.assertEqual(record["connection"]["model_note"], "preferred_model_unavailable")
        self.assertEqual(record["summary"]["requested_model"], "nvidia/Nemotron-3-Super-120b-a12b")

    def test_stop_ends_a_running_investigation_promptly(self):
        release = threading.Event()

        def slow(key, route, body=None):
            if route == "chat/completions":
                release.wait(10)
            return simulated_transport(key, route, body)
        app, client, _ = self.make(slow)
        run_id, args = self.start(app, client)
        worker = threading.Thread(target=app.state.open_lab.work, args=args)
        worker.start()
        for _ in range(100):
            if "designing" in client.get(f"/api/open-investigations/{run_id}").json()["phase"]:
                break
            time.sleep(0.05)
        headers = {**ACTION, "X-CounterLab-Action": "stop-investigation"}
        started = time.monotonic()
        self.assertEqual(client.post(f"/api/open-investigations/{run_id}/cancel", json={}, headers=headers).status_code, 200)
        worker.join(5)
        release.set()
        self.assertFalse(worker.is_alive())
        self.assertLess(time.monotonic() - started, 3)
        record = client.get(f"/api/open-investigations/{run_id}").json()
        self.assertEqual((record["state"], record["error"]), ("cancelled", "cancelled_by_user"))
        self.assertEqual(record["summary"]["status"], "cancelled")
        self.assertTrue(record["export_available"])
        self.assertEqual(client.post(f"/api/open-investigations/{run_id}/cancel", json={}, headers=headers).status_code, 409)

    def test_stop_interrupts_a_running_sandbox_process(self):
        cancel = threading.Event()
        job = {"action": "measure", "files": {}, "conditions": ["a"], "metrics": ["m"], "seeds": [1], "per_call_seconds": 25,
               "harness": "import time\ndef measure(condition, seed):\n    time.sleep(20)\n    return {'m': 1}\n"}
        threading.Timer(0.5, cancel.set).start()
        started = time.monotonic()
        with self.assertRaises(InvestigationCancelled):
            LocalProcessSandbox().execute(job, cancel=cancel)
        self.assertLess(time.monotonic() - started, 5)

    def test_run_again_reuses_the_verified_inputs_and_lists_overviews(self):
        app, client, _ = self.make()
        first, args = self.start(app, client)
        app.state.open_lab.work(*args)
        second, args = self.start(app, client, example_id=None, reuse_inputs_from=first, question="Same inputs, run again please.")
        app.state.open_lab.work(*args)
        one = client.get(f"/api/open-investigations/{first}").json()
        two = client.get(f"/api/open-investigations/{second}").json()
        self.assertEqual(two["state"], "completed")
        self.assertEqual(two["request"]["reused_inputs_from"], first)
        self.assertEqual([f["path"] for f in one["inputs"]["code_files"]], [f["path"] for f in two["inputs"]["code_files"]])
        listing = {item["id"]: item for item in client.get("/api/open-investigations").json()["items"]}
        self.assertEqual(listing[second]["experiments_measured"], 2)
        self.assertEqual(listing[second]["bets"][0]["outcome"], "held")
        self.assertTrue(listing[second]["title"])
        headers = {**ACTION, "X-CounterLab-Action": "archive-investigation"}
        self.assertEqual(client.post(f"/api/open-investigations/{first}/archive", json={}, headers=headers).status_code, 200)
        self.assertNotIn(first, {item["id"] for item in client.get("/api/open-investigations").json()["items"]})

    def test_a_promoted_run_stays_listed_as_yours_in_your_workspace(self):
        import counterlab.open_lab.service as service
        app, client, _ = self.make()
        run_id, args = self.start(app, client)
        app.state.open_lab.work(*args)
        recorded = self.directory / "recorded"
        recorded.mkdir()
        with patch.object(service, "RECORDED", recorded):
            service.promote(app.state.open_lab.run_root, run_id)
            items = [item for item in client.get("/api/open-investigations").json()["items"] if item["id"] == run_id]
            self.assertEqual([item["kind"] for item in items], ["live"])
            _, other, _ = self.make()
            listed = [item for item in other.get("/api/open-investigations").json()["items"] if item["id"] == run_id]
            self.assertEqual([item["kind"] for item in listed], ["recorded"])

    def test_sandbox_setup_reports_a_missing_docker_clearly(self):
        app, client, _ = self.make()
        headers = {**ACTION, "X-CounterLab-Action": "setup-sandbox"}
        with patch("scripts.setup_open_runner.docker_available", return_value=False):
            self.assertEqual(client.post("/api/sandbox/setup", json={}, headers=headers).status_code, 202)
            for _ in range(100):
                state = client.get("/api/sandbox").json()["setup"]
                if state["state"] != "building":
                    break
                time.sleep(0.05)
        self.assertEqual(state["state"], "failed")
        self.assertIn("Docker is not running", state["message"])


if __name__ == "__main__":
    unittest.main()
