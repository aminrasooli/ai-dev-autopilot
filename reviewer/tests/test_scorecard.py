"""Scorecard assembly tests. Offline, like everything in this suite.

The scorecard's whole justification is that it *computes* rather than
restates, so these tests target the arithmetic that a hand-written table
gets wrong: the two denominators, and errors leaking into misses or
false positives.
"""

import json
import os
import tempfile
import unittest

from reviewer import scorecard


def make_report(cases, model="test-model", runs_per_case=2, sha=None):
    return {
        "report_format": 1,
        "backend": "fake",
        "model": model,
        "runs_per_case": runs_per_case,
        "corpus": {"case_count": len(cases), "benchmark_version": 2,
                   "sha256": sha or ("a" * 64)},
        "cases": cases,
    }


def case(case_id, defect, runs):
    return {"case_id": case_id, "title": case_id, "defect": defect,
            "language": "python", "runs": runs}


def run(index, detected=None, false_positive=False, status="ok",
        category=False, severity=False, latency=1.0, cost=None):
    record = {"run": index, "status": status, "verdict": "x", "findings": [],
              "metrics": {"latency_seconds": latency, "external_cost_usd": cost}}
    record["score"] = None if status != "ok" else {
        "detected": detected, "false_positive": false_positive,
        "category_correct": category, "severity_correct": severity}
    return record


class SummarizeTests(unittest.TestCase):
    def test_raw_and_completed_denominators_differ_when_a_run_errors(self):
        # The distinction the published headline depends on: one errored
        # defective observation must leave raw at 4 and completed at 3,
        # and must NOT become a miss.
        report = make_report([
            case("d1", True, [run(1, detected=True), run(2, detected=True)]),
            case("d2", True, [run(1, detected=True), run(2, status="error")]),
        ])
        row = scorecard.summarize(report)
        self.assertEqual(row["raw_defect"], 4)
        self.assertEqual(row["completed_defect"], 3)
        self.assertEqual(row["detected"], 3)
        self.assertEqual(row["defect_errors"], 1)
        self.assertEqual(row["completed_defect"] - row["detected"], 0,
                         "an errored observation must not count as a miss")

    def test_clean_errors_do_not_become_false_positives(self):
        report = make_report([
            case("c1", False, [run(1), run(2, false_positive=True)]),
            case("c2", False, [run(1, status="error"), run(2)]),
        ])
        row = scorecard.summarize(report)
        self.assertEqual(row["raw_clean"], 4)
        self.assertEqual(row["completed_clean"], 3)
        self.assertEqual(row["false_positives"], 1)
        self.assertEqual(row["clean_errors"], 1)

    def test_repeatability_counts_cases_not_observations(self):
        report = make_report([
            case("a", True, [run(1, detected=True), run(2, detected=True)]),
            case("s", True, [run(1, detected=True), run(2, detected=False)]),
            case("n", True, [run(1, detected=False), run(2, detected=False)]),
        ])
        row = scorecard.summarize(report)
        self.assertEqual((row["always"], row["sometimes"], row["never"]),
                         (1, 1, 1))

    def test_local_run_reports_no_external_charge_not_zero_dollars(self):
        report = make_report([case("d", True, [run(1, detected=True)])],
                             runs_per_case=1)
        self.assertIsNone(scorecard.summarize(report)["external_cost_usd"])
        self.assertIn("no external model API charge",
                      scorecard._cost(scorecard.summarize(report)))


class RenderTests(unittest.TestCase):
    def _rows(self):
        report = make_report([
            case("d", True, [run(1, detected=True), run(2, status="error")]),
            case("c", False, [run(1), run(2, false_positive=True)]),
        ])
        row = scorecard.summarize(report)
        return {row["corpus_sha256"]: [row]}

    def test_render_emits_both_denominators(self):
        text = scorecard.render(self._rows())
        self.assertIn("detection (raw)", text)
        self.assertIn("detection (completed)", text)
        self.assertIn("clean FP (raw)", text)
        self.assertIn("clean FP (completed)", text)

    def test_render_states_it_is_not_a_ranking_and_has_no_composite(self):
        # ROADMAP §9 failure mode: manufacturing a ranking the data
        # cannot support. The generator must never grow a total column.
        text = scorecard.render(self._rows())
        self.assertIn("not a ranking", text)
        self.assertNotIn("composite score;", text.replace(
            "There is no composite score;", ""))
        self.assertNotIn("| overall |", text.lower())
        self.assertNotIn("| rank |", text.lower())

    def test_render_groups_by_corpus_fingerprint(self):
        report_a = make_report([case("d", True, [run(1, detected=True)])],
                               model="m1", runs_per_case=1, sha="b" * 64)
        report_b = make_report([case("d", True, [run(1, detected=True)])],
                               model="m2", runs_per_case=1, sha="c" * 64)
        rows = {}
        for report in (report_a, report_b):
            row = scorecard.summarize(report)
            rows.setdefault(row["corpus_sha256"], []).append(row)
        text = scorecard.render(rows)
        self.assertEqual(text.count("Full fingerprint:"), 2,
                         "results from different corpora must not share a table")


class CliTests(unittest.TestCase):
    def test_inconsistent_report_is_skipped_not_quoted(self):
        # A report whose numbers do not follow from its own runs must
        # never reach the scorecard.
        report = make_report([case("d", True, [run(1, detected=True)])],
                             runs_per_case=1)
        report["cases"][0]["runs"] = []          # contradicts runs_per_case
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle)
            self.assertEqual(scorecard.main([path]), 2)

    def test_missing_reports_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(scorecard.main([os.path.join(tmp, "nope.json")]), 2)


if __name__ == "__main__":
    unittest.main()


class HarnessProvenanceTests(unittest.TestCase):
    """`eval/SUBMIT.md` requires a harness commit; it is the one required
    field a submitter cannot reconstruct afterwards, so the harness
    records it itself."""

    def test_report_identifies_the_harness_commit(self):
        from reviewer import evaluate
        prov = evaluate._harness_provenance()
        self.assertIn("available", prov)
        if prov["available"]:
            self.assertRegex(prov["commit"], r"^[0-9a-f]{40}$")
            self.assertIn(prov["dirty"], (True, False, None))
        else:
            self.assertIn("reason", prov)

    def test_provenance_never_carries_a_filesystem_path(self):
        # docs/BENCHMARK_METHODOLOGY.md §11: a submitted report must not
        # leak local paths, and a private holdout's path must never
        # appear anywhere. That is why the invocation is not recorded.
        from reviewer import evaluate
        blob = json.dumps(evaluate._harness_provenance())
        self.assertNotIn("/", blob.replace("\\/", ""))

    def test_missing_harness_block_is_tolerated(self):
        # The six already-published reports predate this field; they must
        # keep verifying and keep appearing in the scorecard.
        report = make_report([case("d", True, [run(1, detected=True)])],
                             runs_per_case=1)
        self.assertNotIn("harness", report)
        row = scorecard.summarize(report)
        self.assertEqual(row["detected"], 1)


class CommittedScorecardTests(unittest.TestCase):
    """`eval/results/SCORECARD.md` is generated. Nothing forced it to be
    regenerated when a result file changed, so it could silently describe
    a set of results that no longer exists — the same failure mode that
    already produced a wrong published corpus fingerprint once.

    M5 makes this live: accepting an outside submission adds a report to
    `eval/results/`, and the scorecard must be regenerated in that same
    change rather than drifting until someone notices."""

    def test_committed_scorecard_matches_a_fresh_generation(self):
        import glob as _glob
        from reviewer import scorecard as sc
        root = os.path.dirname(os.path.dirname(os.path.abspath(sc.__file__)))
        committed = os.path.join(root, "eval", "results", "SCORECARD.md")
        if not os.path.exists(committed):
            self.skipTest("no committed scorecard")
        paths = sorted(p for p in _glob.glob(
            os.path.join(root, "eval", "results", "*.json"))
            if "checkpoint" not in os.path.basename(p))
        rows = {}
        for path in paths:
            with open(path, encoding="utf-8") as handle:
                report = json.load(handle)
            errors, _ = sc.verify_report(report, origin=path)
            if errors:
                continue
            row = sc.summarize(report)
            rows.setdefault(row["corpus_sha256"], []).append(row)
        with open(committed, encoding="utf-8") as handle:
            on_disk = handle.read().strip()
        # assertTrue, not assertEqual: assertEqual dumps the whole
        # rendered scorecard as a diff and buries the instruction.
        self.assertTrue(
            on_disk == sc.render(rows).strip(),
            "eval/results/SCORECARD.md is stale. Regenerate it in the same "
            "change that altered eval/results/:\n"
            "  bin/review-scorecard --out eval/results/SCORECARD.md")
