"""Deterministic tests for the pluggable reviewer.

No GPU, no Ollama daemon, no Codex login, no network — every backend call
here goes through a stub (an `opener` for Ollama's HTTP door, a `runner`
for Codex's subprocess door, or the FakeReviewer's script) so this suite
runs the same on a laptop and in CI.

Run directly:  python3 -m unittest discover -s reviewer/tests -v
Run via suite: tests/reviewer.test.sh
"""

import json
import os
import tempfile
import unittest
from unittest import mock

from reviewer import config, evaluate, net, prompt, result
from reviewer.backends import create_backend
from reviewer.backends.claude_code import ClaudeCodeReviewer
from reviewer.backends.codex import NOT_METERED, CodexReviewer
from reviewer.backends.fake import FakeReviewer
from reviewer.backends.ollama import LOCAL_COST_STATEMENT, OllamaReviewer
from reviewer.errors import ConfigError, MalformedResponse, ModelUnavailable, \
    ReviewerUnavailable


class _FakeResponse:
    def __init__(self, status, body_bytes):
        self.status = status
        self._body = body_bytes

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeOpener:
    """Stands in for urllib's opener: returns a fixed status/body, never
    touches a socket."""

    def __init__(self, status, body_obj):
        self.status = status
        self.body = json.dumps(body_obj).encode("utf-8")
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request.full_url)
        self.payloads = getattr(self, "payloads", [])
        self.payloads.append(json.loads(request.data.decode("utf-8")))
        return _FakeResponse(self.status, self.body)


class _RaisingOpener:
    def __init__(self, exc):
        self.exc = exc

    def open(self, request, timeout=None):
        raise self.exc


class ConfigTests(unittest.TestCase):
    def test_codex_is_the_default_with_no_config_present(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ,
                                  {"AI_DEV_HOME": home}, clear=False):
                os.environ.pop("AI_DEV_REVIEWER_CONFIG", None)
                cfg = config.load_config()
        self.assertEqual(cfg, {"backend": "codex"})

    def test_selecting_ollama_via_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reviewer.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"backend": "ollama", "model": "qwen3.6:27b",
                          "endpoint": "http://127.0.0.1:11434", "timeout": 120}, fh)
            cfg = config.load_config(explicit=path)
        self.assertEqual(cfg["backend"], "ollama")
        self.assertEqual(cfg["model"], "qwen3.6:27b")

    def test_unknown_config_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reviewer.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"backend": "codex", "surprise": True}, fh)
            with self.assertRaises(ConfigError):
                config.load_config(explicit=path)

    def test_malformed_json_is_rejected_not_defaulted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reviewer.json")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            with self.assertRaises(ConfigError):
                config.load_config(explicit=path)

    def test_missing_backend_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reviewer.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"model": "x"}, fh)
            with self.assertRaises(ConfigError):
                config.load_config(explicit=path)


class BackendSelectionTests(unittest.TestCase):
    def test_unknown_backend_name_is_a_config_error_not_a_fallback(self):
        with self.assertRaises(ConfigError):
            create_backend({"backend": "gpt-magic"})

    def test_codex_selected_by_default_config(self):
        backend = create_backend({"backend": "codex"})
        self.assertIsInstance(backend, CodexReviewer)
        self.assertTrue(backend.external_service_required)

    def test_ollama_selected_with_model(self):
        backend = create_backend({"backend": "ollama", "model": "llama3"})
        self.assertIsInstance(backend, OllamaReviewer)
        self.assertFalse(backend.external_service_required)


class NetLoopbackTests(unittest.TestCase):
    def test_default_localhost_endpoint_accepted(self):
        self.assertTrue(net.is_local_url("http://127.0.0.1:11434"))
        self.assertTrue(net.is_local_url("http://localhost:11434"))
        net.require_local("http://127.0.0.1:11434")  # must not raise

    def test_remote_endpoint_rejected_by_default(self):
        for url in ("http://example.com:11434", "http://10.0.0.5:11434",
                    "https://ollama.internal.corp"):
            with self.assertRaises(ConfigError):
                net.require_local(url)

    def test_ollama_backend_refuses_remote_endpoint_at_construction(self):
        with self.assertRaises(ConfigError):
            OllamaReviewer(model="llama3", endpoint="http://example.com:11434")

    def test_ollama_backend_never_falls_back_to_a_second_host(self):
        # A remote-endpoint attempt must fail before any request — including
        # one dressed up as loopback in the path but not the host.
        with self.assertRaises(ConfigError):
            OllamaReviewer(model="llama3",
                           endpoint="http://attacker.example/127.0.0.1")


class OllamaBackendTests(unittest.TestCase):
    def test_daemon_unreachable_is_reviewerunavailable(self):
        backend = OllamaReviewer(model="llama3",
                                 opener=_RaisingOpener(OSError("connection refused")))
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_missing_model_is_modelunavailable(self):
        backend = OllamaReviewer(
            model="ghost-model",
            opener=_FakeOpener(404, {"error": "model 'ghost-model' not found"}))
        with self.assertRaises(ModelUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_preflight_reports_missing_model_without_raising(self):
        backend = OllamaReviewer(
            model="ghost-model",
            opener=_FakeOpener(404, {"error": "model 'ghost-model' not found"}))
        check = backend.preflight()
        self.assertFalse(check["ok"])
        self.assertIn("not installed", check["detail"])

    def test_preflight_ok_when_model_present(self):
        backend = OllamaReviewer(model="llama3", opener=_FakeOpener(200, {}))
        check = backend.preflight()
        self.assertTrue(check["ok"])

    def test_prose_instead_of_json_is_malformed(self):
        body = {"response": "Looks fine to me, no issues here!",
                "prompt_eval_count": 10, "eval_count": 5}
        backend = OllamaReviewer(model="llama3", opener=_FakeOpener(200, body))
        with self.assertRaises(MalformedResponse):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_happy_path_reports_tokens_and_local_cost_statement(self):
        reply = json.dumps({"findings": [], "verdict": "approve"})
        body = {"response": reply, "prompt_eval_count": 42, "eval_count": 7,
                "total_duration": 2_500_000_000}
        backend = OllamaReviewer(model="llama3", opener=_FakeOpener(200, body))
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(review.verdict, "approve")
        self.assertEqual(review.metrics.input_tokens, 42)
        self.assertEqual(review.metrics.output_tokens, 7)
        self.assertEqual(review.metrics.local_execution_seconds, 2.5)
        self.assertEqual(review.metrics.external_cost, LOCAL_COST_STATEMENT)
        self.assertFalse(review.metrics.external_service_required)

    def test_request_disables_thinking_mode(self):
        # Some reasoning models route the whole answer into a separate
        # 'thinking' field and leave 'response' empty unless told not to
        # reason at all — see test_entire_answer_in_thinking_field_is_
        # reported_clearly below for the failure this prevents.
        opener = _FakeOpener(200, {"response": json.dumps(
            {"findings": [], "verdict": "approve"})})
        backend = OllamaReviewer(model="llama3", opener=opener)
        backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(opener.payloads[0]["think"], False)

    def test_entire_answer_in_thinking_field_is_reported_clearly(self):
        # Reproduces the real qwen3.6:27b failure mode: done_reason "stop",
        # a valid JSON answer sitting in 'thinking', and an empty
        # 'response' — not truncation, not garbage, just the wrong field.
        body = {"response": "", "thinking": '{"findings": [], "verdict": "approve"}',
                "done_reason": "stop"}
        backend = OllamaReviewer(model="llama3", opener=_FakeOpener(200, body))
        with self.assertRaises(MalformedResponse) as ctx:
            backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertIn("thinking", str(ctx.exception))

    def test_no_silent_cloud_fallback_on_failure(self):
        opener = _RaisingOpener(OSError("connection refused"))
        backend = OllamaReviewer(model="llama3", opener=opener)
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")
        # The only door this backend has is its own opener against its own
        # loopback endpoint; there is no code path that reaches for another.
        self.assertTrue(backend.endpoint.startswith("http://127.0.0.1"))


class CodexBackendTests(unittest.TestCase):
    class _AlwaysOk(CodexReviewer):
        def preflight(self):
            return {"ok": True, "detail": "stub"}

    def test_cost_is_reported_as_not_metered_never_invented(self):
        reply = json.dumps({"findings": [], "verdict": "approve"})
        backend = self._AlwaysOk(runner=lambda *a, **k: (0, reply))
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(review.metrics.external_cost, NOT_METERED)
        self.assertIsNone(review.metrics.input_tokens)
        self.assertIsNone(review.metrics.output_tokens)
        self.assertTrue(review.metrics.external_service_required)

    def test_timeout_is_reviewerunavailable(self):
        backend = self._AlwaysOk(runner=lambda *a, **k: (124, ""))
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_empty_output_is_malformed(self):
        backend = self._AlwaysOk(runner=lambda *a, **k: (0, ""))
        with self.assertRaises(MalformedResponse):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_credential_env_vars_are_not_forwarded(self):
        seen_env = {}

        def capture_runner(cmd, stdin_text, timeout, env):
            seen_env.update(env)
            return 0, json.dumps({"findings": [], "verdict": "approve"})

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-should-not-leak"}):
            backend = self._AlwaysOk(runner=capture_runner)
            backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertNotIn("OPENAI_API_KEY", seen_env)


class ClaudeCodeBackendTests(unittest.TestCase):
    @staticmethod
    def _envelope(result_text, **extra):
        env = {"is_error": False, "result": result_text,
              "usage": {"input_tokens": 10, "output_tokens": 5},
              "total_cost_usd": 0.0123}
        env.update(extra)
        return json.dumps(env)

    def test_cost_is_measured_from_the_tool_never_invented(self):
        # The dollar figure lives in external_cost_usd, never baked into
        # the external_cost label — a label with a different number on
        # every call can't be deduped by evaluate.aggregate().
        reply = self._envelope(json.dumps({"findings": [], "verdict": "approve"}))
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (0, reply))
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(review.metrics.external_cost_usd, 0.0123)
        self.assertIn("measured", review.metrics.external_cost)
        self.assertNotIn("0.0123", review.metrics.external_cost)
        self.assertEqual(review.metrics.output_tokens, 5)

    def test_input_tokens_include_cache_creation_and_cache_read(self):
        # 'input_tokens' alone only counts uncached tokens; prompt caching
        # can put nearly the whole prompt into cache_creation/cache_read
        # instead, which must still count as real input for this call.
        reply = self._envelope(json.dumps({"findings": [], "verdict": "approve"}),
                               usage={"input_tokens": 1, "cache_creation_input_tokens": 800,
                                     "cache_read_input_tokens": 50, "output_tokens": 20})
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (0, reply))
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(review.metrics.input_tokens, 851)

    def test_missing_cost_field_stays_none_not_zero(self):
        reply = self._envelope(json.dumps({"findings": [], "verdict": "approve"}))
        env = json.loads(reply)
        del env["total_cost_usd"]
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (0, json.dumps(env)))
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertIsNone(review.metrics.external_cost_usd)

    def test_timeout_is_reviewerunavailable(self):
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (124, ""))
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_is_error_envelope_is_reviewerunavailable_not_malformed(self):
        reply = self._envelope("permission denied", **{"is_error": True})
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (0, reply))
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_non_json_stdout_is_malformed(self):
        backend = ClaudeCodeReviewer(runner=lambda *a, **k: (0, "not an envelope"))
        with self.assertRaises(MalformedResponse):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_isolation_flags_present_in_the_real_command(self):
        # The default runner must run isolated from this repository and
        # this session: no tools, a system prompt that replaces (not
        # appends to) the default one, and no user/project settings — see
        # reviewer/backends/claude_code.py for why each of these matters.
        from reviewer.backends.claude_code import _default_runner

        captured = {}

        def fake_run(cmd, cwd=None, capture_output=None, text=None, timeout=None, env=None):
            captured["cmd"] = cmd
            captured["cwd"] = cwd
            captured["env"] = env

            class _Proc:
                returncode = 0
                stdout = json.dumps({"is_error": False, "result": "{}"})
            return _Proc()

        with mock.patch("subprocess.run", fake_run):
            _default_runner("claude-sonnet-5", "review this", 60)
        cmd = captured["cmd"]
        self.assertIn("--tools", cmd)
        self.assertEqual(cmd[cmd.index("--tools") + 1], "")
        self.assertIn("--system-prompt", cmd)
        self.assertIn("--setting-sources", cmd)
        self.assertEqual(cmd[cmd.index("--setting-sources") + 1], "")
        self.assertNotEqual(captured["cwd"], os.getcwd())

    def test_non_anthropic_credentials_are_not_forwarded(self):
        seen_env = {}

        def capture(cmd, cwd=None, capture_output=None, text=None, timeout=None, env=None):
            seen_env.update(env or {})

            class _Proc:
                returncode = 0
                stdout = json.dumps({"is_error": False,
                                     "result": json.dumps({"findings": [], "verdict": "approve"})})
            return _Proc()

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-should-not-leak",
                                           "ANTHROPIC_API_KEY": "should-be-kept"}):
            with mock.patch("subprocess.run", capture):
                backend = ClaudeCodeReviewer()
                backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertNotIn("OPENAI_API_KEY", seen_env)
        self.assertEqual(seen_env.get("ANTHROPIC_API_KEY"), "should-be-kept")


class FakeBackendTests(unittest.TestCase):
    def test_scripted_json_reply_goes_through_the_real_contract(self):
        script = {"default": {"findings": [], "verdict": "approve"}}
        backend = FakeReviewer(script=script)
        review = backend.review_diff("--- a/f\n+++ b/f\n")
        self.assertEqual(review.verdict, "approve")

    def test_scripted_prose_reply_proves_the_malformed_path(self):
        backend = FakeReviewer(script={"default": "not json at all"})
        with self.assertRaises(MalformedResponse):
            backend.review_diff("--- a/f\n+++ b/f\n")

    def test_unhealthy_backend_raises_reviewerunavailable(self):
        backend = FakeReviewer(healthy=False)
        with self.assertRaises(ReviewerUnavailable):
            backend.review_diff("--- a/f\n+++ b/f\n")


class ResultSchemaTests(unittest.TestCase):
    def test_ollama_and_fake_produce_the_same_result_shape(self):
        reply = json.dumps({"findings": [], "verdict": "approve"})
        ollama = OllamaReviewer(
            model="llama3",
            opener=_FakeOpener(200, {"response": reply}))
        fake = FakeReviewer(script={"default": {"findings": [], "verdict": "approve"}})
        r1 = ollama.review_diff("--- a/f\n+++ b/f\n").to_dict()
        r2 = fake.review_diff("--- a/f\n+++ b/f\n").to_dict()
        self.assertEqual(set(r1), set(r2))
        self.assertEqual(set(r1["metrics"]), set(r2["metrics"]))

    def test_cost_unknown_never_defaults_to_zero(self):
        metrics = result.ReviewMetrics(backend="x", model="y", latency_seconds=1.0)
        self.assertEqual(metrics.external_cost, "unknown")
        self.assertIsNone(metrics.input_tokens)

    def test_malformed_findings_reject_off_vocabulary_category(self):
        obj = result.parse_json_output(json.dumps(
            {"findings": [{"category": "vibes", "severity": "high",
                          "file": None, "note": "x"}], "verdict": "changes_required"}))
        with self.assertRaises(MalformedResponse):
            result.validate_review_output(obj)

    def test_bare_and_fenced_json_both_parse(self):
        obj = {"findings": [], "verdict": "approve"}
        bare = result.parse_json_output(json.dumps(obj))
        fenced = result.parse_json_output("```json\n" + json.dumps(obj) + "\n```")
        self.assertEqual(bare, fenced)

    def test_prompt_is_identical_regardless_of_backend(self):
        # The eval only means something if no backend gets an easier prompt.
        p1 = prompt.build_review_prompt("diff-a")
        p2 = prompt.build_review_prompt("diff-a")
        self.assertEqual(p1, p2)
        self.assertIn("diff-a", p1)


class EvalHarnessTests(unittest.TestCase):
    def test_load_cases_delegates_to_the_corpus_validator(self):
        # Schema enforcement itself is tested in test_corpus.py; here we
        # prove the eval loads through that same door.
        from .test_corpus import make_case, write_corpus
        with tempfile.TemporaryDirectory() as tmp:
            write_corpus(tmp, make_case("via-eval"))
            cases = evaluate.load_cases(tmp)
        self.assertEqual(len(cases), 1)
        self.assertIsInstance(cases[0]["diff"], str)

    def test_load_cases_rejects_an_invalid_corpus(self):
        from .test_corpus import make_case, write_corpus
        with tempfile.TemporaryDirectory() as tmp:
            bad = make_case("bad-sev")
            bad["ground_truth"]["severity"] = ["high", "low"]
            write_corpus(tmp, bad)
            with self.assertRaises(ConfigError):
                evaluate.load_cases(tmp)

    def test_false_positive_scoring_on_clean_case(self):
        case = {"ground_truth": {"defect": False}}
        review = result.ReviewResult(
            "changes_required",
            [{"category": "other", "severity": "low", "file": None, "note": "n"}],
            result.ReviewMetrics(backend="x", model="y", latency_seconds=0))
        score = evaluate.score_case(case, review)
        self.assertTrue(score["false_positive"])
        self.assertIsNone(score["detected"])

    def test_miss_scoring_on_defect_case_with_no_findings(self):
        case = {"ground_truth": {"defect": True, "category": "logic-error",
                                 "severity": ["medium", "high"]}}
        review = result.ReviewResult(
            "approve", [], result.ReviewMetrics(backend="x", model="y", latency_seconds=0))
        score = evaluate.score_case(case, review)
        self.assertFalse(score["detected"])
        self.assertFalse(score["category_correct"])

    def test_category_and_severity_correct_when_finding_matches(self):
        case = {"ground_truth": {"defect": True, "category": "logic-error",
                                 "severity": ["medium", "high"]}}
        review = result.ReviewResult(
            "changes_required",
            [{"category": "logic-error", "severity": "high", "file": None, "note": "n"}],
            result.ReviewMetrics(backend="x", model="y", latency_seconds=0))
        score = evaluate.score_case(case, review)
        self.assertTrue(score["detected"])
        self.assertTrue(score["category_correct"])
        self.assertTrue(score["severity_correct"])

    def test_severity_outside_range_is_not_severity_correct(self):
        case = {"ground_truth": {"defect": True, "category": "logic-error",
                                 "severity": ["medium", "high"]}}
        review = result.ReviewResult(
            "changes_required",
            [{"category": "logic-error", "severity": "low", "file": None, "note": "n"}],
            result.ReviewMetrics(backend="x", model="y", latency_seconds=0))
        score = evaluate.score_case(case, review)
        self.assertTrue(score["detected"])
        self.assertTrue(score["category_correct"])
        self.assertFalse(score["severity_correct"])

    def test_aggregation_keeps_unknown_tokens_as_none_not_zero(self):
        records = [
            {"status": "ok", "defect": True,
             "score": {"detected": True, "false_positive": False,
                      "category_correct": True, "severity_correct": True},
             "metrics": {"latency_seconds": 1.0, "input_tokens": None,
                        "output_tokens": None,
                        "external_cost": NOT_METERED}},
            {"status": "error", "defect": True, "error": "boom"},
        ]
        summary = evaluate.aggregate(records)
        self.assertEqual(summary["cases"], 2)
        self.assertEqual(summary["errors"], 1)
        self.assertIsNone(summary["total_input_tokens"])
        self.assertEqual(summary["external_cost"], [NOT_METERED])

    def test_aggregation_sums_tokens_when_at_least_one_record_reports_them(self):
        records = [
            {"status": "ok", "defect": False,
             "score": {"detected": None, "false_positive": False,
                      "category_correct": None, "severity_correct": None},
             "metrics": {"latency_seconds": 1.0, "input_tokens": 10,
                        "output_tokens": 5, "external_cost": "unknown"}},
        ]
        summary = evaluate.aggregate(records)
        self.assertEqual(summary["total_input_tokens"], 10)
        self.assertEqual(summary["total_output_tokens"], 5)

    def test_aggregation_sums_real_dollar_costs_across_calls(self):
        # Each call reports its OWN dollar figure (unlike Codex/Ollama's
        # fixed label) — aggregate() must sum them, not just dedupe
        # distinct strings, or a 20-case run never shows a total.
        records = [
            {"status": "ok", "defect": False,
             "score": {"detected": None, "false_positive": False,
                      "category_correct": None, "severity_correct": None},
             "metrics": {"latency_seconds": 1.0, "input_tokens": 10, "output_tokens": 5,
                        "external_cost": "measured (claude --output-format json)",
                        "external_cost_usd": 0.01}},
            {"status": "ok", "defect": False,
             "score": {"detected": None, "false_positive": False,
                      "category_correct": None, "severity_correct": None},
             "metrics": {"latency_seconds": 1.0, "input_tokens": 10, "output_tokens": 5,
                        "external_cost": "measured (claude --output-format json)",
                        "external_cost_usd": 0.02}},
        ]
        summary = evaluate.aggregate(records)
        self.assertEqual(summary["total_external_cost_usd"], 0.03)
        # The label itself still dedupes to one entry, same as Codex/Ollama.
        self.assertEqual(summary["external_cost"],
                         ["measured (claude --output-format json)"])

    def test_aggregation_cost_stays_none_when_nothing_reports_a_dollar_figure(self):
        records = [
            {"status": "ok", "defect": False,
             "score": {"detected": None, "false_positive": False,
                      "category_correct": None, "severity_correct": None},
             "metrics": {"latency_seconds": 1.0, "input_tokens": 10, "output_tokens": 5,
                        "external_cost": "no external model API charge (local compute time is not free)"}},
        ]
        summary = evaluate.aggregate(records)
        self.assertIsNone(summary["total_external_cost_usd"])

    def test_comparison_columns_stay_separated_for_long_values(self):
        # Column width used to be sized from the header alone; a value
        # longer than the header (e.g. a long external_cost label) ran
        # straight into the next column with no separating space.
        long_label = "measured (claude --output-format json)"
        report_a = {"backend": "claude", "model": "claude-sonnet-5",
                   "summary": {"detected": 15, "defect_cases": 15, "missed": 0,
                              "false_positives": 0, "category_correct": 14,
                              "severity_correct": 14, "errors": 0,
                              "mean_latency_seconds": 4.1,
                              "external_cost": [long_label],
                              "total_external_cost_usd": 0.107230}}
        report_b = {"backend": "ollama", "model": "qwen3.6:27b",
                   "summary": {"detected": 15, "defect_cases": 15, "missed": 0,
                              "false_positives": 0, "category_correct": 11,
                              "severity_correct": 10, "errors": 0,
                              "mean_latency_seconds": 7.8,
                              "external_cost": ["no external model API charge"],
                              "total_external_cost_usd": None}}
        table = evaluate.render_comparison(report_a, report_b)
        cost_line = next(line for line in table.splitlines()
                         if line.startswith("external cost"))
        self.assertIn(long_label + " ", cost_line)

    def test_real_corpus_loads_and_the_oracle_scores_it_perfectly(self):
        # Regression guard for the actual eval/cases/ shipped in the repo:
        # the oracle (built straight from ground truth) must score 100% or
        # the harness itself — not any model — has a bug.
        cases = evaluate.load_cases(evaluate.DEFAULT_CASES_DIR)
        self.assertEqual(len(cases), 53)
        backend = evaluate.oracle_backend(cases)
        report = evaluate.run_eval(backend, cases)
        summary = report["summary"]
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["detected"], summary["defect_cases"])
        self.assertEqual(summary["missed"], 0)
        self.assertEqual(summary["false_positives"], 0)
        self.assertEqual(summary["category_correct"], summary["defect_cases"])
        self.assertEqual(summary["severity_correct"], summary["defect_cases"])


class _ScriptedRunsBackend:
    """Duck-typed backend whose answer differs per call: exactly the shape
    of nondeterminism --runs exists to expose. Each entry is either a
    findings list or an exception to raise."""

    name = "stub"
    model = "scripted"
    external_service_required = False

    def __init__(self, replies):
        self.replies = list(replies)

    def preflight(self):
        return {"ok": True, "detail": "stub"}

    def review_diff(self, diff_text, context=None):
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        verdict = "changes_required" if reply else "approve"
        metrics = result.ReviewMetrics(backend=self.name, model=self.model,
                                       latency_seconds=0.1)
        return result.ReviewResult(verdict, reply, metrics)


def _finding(category="logic-error", severity="medium"):
    return {"category": category, "severity": severity,
            "file": None, "note": "n"}


class RepeatRunTests(unittest.TestCase):
    def _clean_case(self):
        from .test_corpus import make_case
        case = make_case("clean-under-repeat", defect=False)
        case["diff"] = case["diff"][:-1] + ["+new_clean_under_repeat"]
        return case

    def test_each_case_runs_n_times_and_raw_runs_are_preserved(self):
        from .test_corpus import make_case
        cases = [make_case("rep-a"), make_case("rep-b", defect=False)]
        for case in cases:
            case["diff"] = "\n".join(case["diff"]) + "\n"
        backend = evaluate.oracle_backend(cases)
        report = evaluate.run_eval(backend, cases, runs=3)
        self.assertEqual(report["runs_per_case"], 3)
        for record in report["cases"]:
            self.assertEqual(len(record["runs"]), 3)
            self.assertEqual({r["run"] for r in record["runs"]}, {1, 2, 3})
        self.assertEqual(report["summary"]["cases"], 6)  # run-level count
        c = report["summary"]["consistency"]
        self.assertEqual(c["defect_cases_always_detected"], 1)
        self.assertEqual(c["clean_cases_ever_false_positive"], 0)

    def test_flaky_clean_case_reports_partial_false_positives(self):
        case = self._clean_case()
        case["diff"] = "\n".join(case["diff"]) + "\n"
        backend = _ScriptedRunsBackend([[_finding()], [], []])
        report = evaluate.run_eval(backend, [case], runs=3)
        record = report["cases"][0]
        self.assertEqual(record["consistency"]["false_positive_runs"], 1)
        self.assertEqual(record["consistency"]["ok_runs"], 3)
        # Run-level and case-level views must both say "1 of 3", never a
        # flattened binary.
        self.assertEqual(report["summary"]["false_positives"], 1)
        self.assertEqual(
            report["summary"]["consistency"]["clean_cases_ever_false_positive"], 1)

    def test_errored_run_is_recorded_and_the_eval_continues(self):
        from .test_corpus import make_case
        case = make_case("err-mid-run")
        case["diff"] = "\n".join(case["diff"]) + "\n"
        backend = _ScriptedRunsBackend(
            [[_finding()], ReviewerUnavailable("daemon down"), [_finding()]])
        report = evaluate.run_eval(backend, [case], runs=3)
        record = report["cases"][0]
        self.assertEqual(record["consistency"]["error_runs"], 1)
        self.assertEqual(record["consistency"]["detected_runs"], 2)
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertEqual(
            report["summary"]["consistency"]["cases_with_errors"], 1)

    def test_sometimes_detected_case_is_neither_always_nor_never(self):
        from .test_corpus import make_case
        case = make_case("flaky-detect")
        case["diff"] = "\n".join(case["diff"]) + "\n"
        backend = _ScriptedRunsBackend([[_finding()], [], []])
        report = evaluate.run_eval(backend, [case], runs=3)
        c = report["summary"]["consistency"]
        self.assertEqual(c["defect_cases_sometimes_detected"], 1)
        self.assertEqual(c["defect_cases_always_detected"], 0)
        self.assertEqual(c["defect_cases_never_detected"], 0)

    def test_progress_callback_fires_once_per_run(self):
        from .test_corpus import make_case
        cases = [make_case("prog-a"), make_case("prog-b")]
        for case in cases:
            case["diff"] = "\n".join(case["diff"]) + "\n"
        lines = []
        backend = evaluate.oracle_backend(cases)
        evaluate.run_eval(backend, cases, runs=2, progress=lines.append)
        self.assertEqual(len(lines), 4)
        self.assertIn("case 1/2", lines[0])
        self.assertIn("run 2/2", lines[3])

    def test_default_single_run_keeps_v1_summary_semantics(self):
        from .test_corpus import make_case
        case = make_case("single-run")
        case["diff"] = "\n".join(case["diff"]) + "\n"
        backend = evaluate.oracle_backend([case])
        report = evaluate.run_eval(backend, [case])
        self.assertEqual(report["runs_per_case"], 1)
        self.assertEqual(report["summary"]["cases"], 1)
        self.assertEqual(report["summary"]["detected"], 1)
        self.assertEqual(len(report["cases"][0]["runs"]), 1)
        # A report must identify its corpus by counts and content
        # fingerprint, never by local path.
        self.assertEqual(report["corpus"]["case_count"], 1)
        self.assertEqual(report["corpus"]["benchmark_version"], 2)
        self.assertEqual(len(report["corpus"]["sha256"]), 64)
        self.assertNotIn("/", json.dumps(report["corpus"]))


if __name__ == "__main__":
    unittest.main()
