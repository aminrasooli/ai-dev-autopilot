"""Report-integrity, variance-analysis and failure-injection tests.

Deterministic and offline: every "model" here is a scripted stub.
"""

import copy
import json
import os
import tempfile
import unittest

from reviewer import analyze, evaluate, result, verify
from reviewer.errors import MalformedResponse, ReviewerUnavailable

from .test_corpus import make_case


class _Scripted:
    """Backend whose per-call answer is scripted; entries are either a
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
        metrics = result.ReviewMetrics(backend=self.name, model=self.model,
                                       latency_seconds=0.1, input_tokens=10,
                                       output_tokens=5, external_cost_usd=0.001)
        return result.ReviewResult(
            "changes_required" if reply else "approve", reply, metrics)


def _finding(category="logic-error", severity="medium"):
    return {"category": category, "severity": severity, "file": None, "note": "n"}


def _corpus(*cases):
    for case in cases:
        case["diff"] = "\n".join(case["diff"]) + "\n" \
            if isinstance(case["diff"], list) else case["diff"]
    return list(cases)


class ReportIntegrityTests(unittest.TestCase):
    def _report(self):
        cases = _corpus(make_case("int-a"), make_case("int-b", defect=False))
        backend = _Scripted([[_finding()], [_finding()], [], []])
        return evaluate.run_eval(backend, cases, runs=2), cases

    def test_untouched_report_is_consistent(self):
        report, _ = self._report()
        errors, _ = verify.verify_report(report)
        self.assertEqual(errors, [])

    def test_tampered_summary_is_caught(self):
        # The failure this exists for: a headline edited to look better
        # while the raw runs beneath it say otherwise.
        report, _ = self._report()
        report["summary"]["detected"] += 1
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("summary.detected" in e for e in errors), errors)

    def test_tampered_false_positive_count_is_caught(self):
        report, _ = self._report()
        report["summary"]["false_positives"] = 0
        report["summary"]["clean_cases"] = 99
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("summary.clean_cases" in e for e in errors), errors)

    def test_deleted_run_is_caught(self):
        report, _ = self._report()
        report["cases"][0]["runs"].pop()
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("runs, expected" in e for e in errors), errors)

    def test_case_count_disagreement_is_caught(self):
        report, _ = self._report()
        report["corpus"]["case_count"] = 99
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("case_count" in e for e in errors), errors)

    def test_tampered_consistency_block_is_caught(self):
        report, _ = self._report()
        report["cases"][0]["consistency"]["error_runs"] = 7
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("consistency.error_runs" in e for e in errors), errors)

    def test_duplicate_case_ids_rejected(self):
        report, _ = self._report()
        report["cases"][1]["case_id"] = report["cases"][0]["case_id"]
        report["corpus"]["case_count"] = 2
        errors, _ = verify.verify_report(report)
        self.assertTrue(any("duplicate case_id" in e for e in errors), errors)

    def test_missing_prompt_contract_is_a_warning_not_an_error(self):
        report, _ = self._report()
        del report["prompt_contract"]
        errors, warnings = verify.verify_report(report)
        self.assertEqual(errors, [])
        self.assertTrue(any("L0" in w for w in warnings))

    def test_cli_round_trip(self):
        report, _ = self._report()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(report, fh)
            self.assertEqual(verify.main([path]), 0)
            report["summary"]["missed"] = 42
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(report, fh)
            self.assertEqual(verify.main([path]), 2)


class FailureInjectionTests(unittest.TestCase):
    """Backend failures must never be scored as model quality."""

    def _run(self, replies, case=None, runs=3):
        cases = _corpus(case or make_case("inj"))
        return evaluate.run_eval(_Scripted(replies), cases, runs=runs), cases

    def test_timeout_is_an_error_not_a_miss(self):
        report, _ = self._run(
            [[_finding()], ReviewerUnavailable("timed out after 600s"), [_finding()]])
        s = report["summary"]
        self.assertEqual(s["errors"], 1)
        # Two ok runs, both detected: the timeout must not appear as a miss.
        self.assertEqual(s["missed"], 0)
        self.assertEqual(s["detected"], 2)

    def test_malformed_response_is_an_error_not_a_miss(self):
        report, _ = self._run(
            [MalformedResponse("prose, not JSON"), [_finding()], [_finding()]])
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertEqual(report["summary"]["missed"], 0)

    def test_backend_unavailable_for_every_run_yields_no_false_score(self):
        report, _ = self._run([ReviewerUnavailable("daemon down")] * 3)
        s = report["summary"]
        self.assertEqual(s["errors"], 3)
        self.assertEqual(s["detected"], 0)
        self.assertEqual(s["missed"], 0)   # nothing was scored at all
        self.assertEqual(s["defect_cases"], 0)

    def test_one_case_failing_does_not_abort_the_others(self):
        cases = _corpus(make_case("fail-me"), make_case("fine"))
        backend = _Scripted([ReviewerUnavailable("boom"), [_finding()]])
        report = evaluate.run_eval(backend, cases, runs=1)
        self.assertEqual(len(report["cases"]), 2)
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertEqual(report["summary"]["detected"], 1)

    def test_missing_cost_and_tokens_stay_none_not_zero(self):
        class _NoMetrics(_Scripted):
            def review_diff(self, diff_text, context=None):
                self.replies.pop(0)
                return result.ReviewResult(
                    "approve", [],
                    result.ReviewMetrics(backend="stub", model="m",
                                         latency_seconds=0.1))
        cases = _corpus(make_case("nom", defect=False))
        report = evaluate.run_eval(_NoMetrics([[]]), cases, runs=1)
        s = report["summary"]
        self.assertIsNone(s["total_input_tokens"])
        self.assertIsNone(s["total_external_cost_usd"])

    def test_error_reports_still_verify(self):
        report, _ = self._run([ReviewerUnavailable("x"), [_finding()], [_finding()]])
        errors, _ = verify.verify_report(report)
        self.assertEqual(errors, [])


class VarianceAnalysisTests(unittest.TestCase):
    def test_wilson_interval_bounds_and_shape(self):
        low, high = analyze.wilson_interval(3, 3)
        self.assertLess(low, 1.0)          # never claims certainty from n=3
        self.assertEqual(high, 1.0)
        self.assertEqual(analyze.wilson_interval(0, 0), (0.0, 0.0))
        # More data must not widen the interval.
        narrow = analyze.wilson_interval(50, 100)
        wide = analyze.wilson_interval(5, 10)
        self.assertLess(narrow[1] - narrow[0], wide[1] - wide[0])

    def test_stability_labels(self):
        cases = _corpus(make_case("flaky"), make_case("cleanish", defect=False))
        backend = _Scripted([[_finding()], [], [_finding()],      # flaky: 2/3
                             [], [_finding()], []])               # clean: 1/3 fp
        report = evaluate.run_eval(backend, cases, runs=3)
        rows = {r["case_id"]: r for r in analyze.case_stability(report)}
        self.assertEqual(rows["flaky"]["stability"], "sometimes")
        self.assertEqual(rows["flaky"]["detected_runs"], 2)
        self.assertEqual(rows["cleanish"]["stability"], "occasional-fp")
        self.assertEqual(rows["cleanish"]["false_positive_runs"], 1)

    def test_slices_and_unstable_listing(self):
        cases = _corpus(make_case("s1"), make_case("s2", language="go"),
                        make_case("s3", defect=False))
        backend = _Scripted([[_finding()], [_finding()],   # s1 always
                             [_finding()], [],             # s2 sometimes
                             [], []])                      # s3 clean
        report = evaluate.run_eval(backend, cases, runs=2)
        a = analyze.analyze(report, cases)
        self.assertEqual(a["stability"]["defect_always_detected"], 1)
        self.assertEqual(a["stability"]["defect_sometimes_detected"], 1)
        self.assertEqual(a["stability"]["clean_never_fp"], 1)
        self.assertIn("go", a["by_language"])
        self.assertIn("moderate", a["by_difficulty"])
        self.assertEqual([r["case_id"] for r in a["unstable_cases"]], ["s2"])
        self.assertIn("recall_ci95", a["overall"])
        self.assertIn("variance analysis", analyze.render(a))


class ExternalCorpusTests(unittest.TestCase):
    """The holdout path: an arbitrary directory must work end to end,
    and must never leak into the report."""

    def test_external_directory_runs_and_leaks_no_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in (make_case("ext-a"), make_case("ext-b", defect=False)):
                with open(os.path.join(tmp, case["id"] + ".json"), "w",
                          encoding="utf-8") as fh:
                    json.dump(case, fh)
            cases = evaluate.load_cases(tmp)
            backend = evaluate.oracle_backend(cases)
            report = evaluate.run_eval(backend, cases, runs=2)
        self.assertEqual(report["corpus"]["case_count"], 2)
        self.assertEqual(len(report["corpus"]["sha256"]), 64)
        blob = json.dumps(report)
        self.assertNotIn(tmp, blob)
        self.assertNotIn("/tmp", blob)
        errors, _ = verify.verify_report(report)
        self.assertEqual(errors, [])

    def test_external_corpus_fingerprint_differs_from_public(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case("ext-only")
            with open(os.path.join(tmp, "ext-only.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(case, fh)
            ext = evaluate.load_cases(tmp)
        public = evaluate.load_cases(evaluate.DEFAULT_CASES_DIR)
        from reviewer.corpus import corpus_fingerprint
        self.assertNotEqual(corpus_fingerprint(ext), corpus_fingerprint(public))


if __name__ == "__main__":
    unittest.main()
