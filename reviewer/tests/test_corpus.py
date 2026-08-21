"""Schema-v2 and corpus-validator tests. Fully offline, like everything
in this suite."""

import copy
import json
import os
import tempfile
import unittest

from reviewer import corpus
from reviewer.errors import ConfigError


def make_case(case_id="widget-check", defect=True, **overrides):
    """A minimal valid v2 case; the id is woven into the diff so distinct
    cases never trip the near-duplicate detector."""
    obj = {
        "benchmark_version": 2,
        "id": case_id,
        "title": "a test case",
        "language": "python",
        "status": "pilot",
        "provenance": {"type": "seeded-synthetic", "author_family": "claude"},
        "affected_files": ["src/app.py"],
        "diff": ["--- a/src/app.py", "+++ b/src/app.py",
                 "@@ -1,2 +1,2 @@", f"-old_{case_id}", f"+new_{case_id}"],
        "ground_truth": (
            {"defect": True, "category": "logic-error",
             "severity": ["medium", "high"], "explanation": "why"}
            if defect else {"defect": False, "explanation": "clean"}),
    }
    obj.update(overrides)
    return obj


def write_corpus(tmp, *cases):
    for case in cases:
        with open(os.path.join(tmp, case["id"] + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(case, fh)


class ValidateCaseTests(unittest.TestCase):
    def assert_rejected(self, case, fragment):
        errors, _ = corpus.validate_case(case)
        self.assertTrue(any(fragment in e for e in errors),
                        f"expected error containing {fragment!r}, got {errors}")

    def test_valid_defective_case_passes(self):
        errors, warnings = corpus.validate_case(make_case())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_clean_case_passes(self):
        errors, _ = corpus.validate_case(make_case(defect=False))
        self.assertEqual(errors, [])

    def test_missing_required_field(self):
        case = make_case()
        del case["language"]
        self.assert_rejected(case, "missing 'language'")

    def test_unknown_top_level_field(self):
        self.assert_rejected(make_case(surprise=True), "unknown fields")

    def test_bad_language(self):
        self.assert_rejected(make_case(language="cobol"), "language")

    def test_bad_provenance_type(self):
        case = make_case(provenance={"type": "dreamed-up",
                                     "author_family": "claude"})
        self.assert_rejected(case, "provenance.type")

    def test_mined_real_fix_requires_reference(self):
        case = make_case(provenance={"type": "mined-real-fix",
                                     "author_family": "human"})
        self.assert_rejected(case, "requires provenance.reference")

    def test_unknown_category_rejected(self):
        case = make_case()
        case["ground_truth"]["category"] = "vibes"
        self.assert_rejected(case, "category")

    def test_inverted_severity_rejected(self):
        case = make_case()
        case["ground_truth"]["severity"] = ["high", "low"]
        self.assert_rejected(case, "severity")

    def test_whole_scale_severity_is_a_warning_not_an_error(self):
        case = make_case()
        case["ground_truth"]["severity"] = ["low", "critical"]
        errors, warnings = corpus.validate_case(case)
        self.assertEqual(errors, [])
        self.assertTrue(any("vacuous" in w for w in warnings))

    def test_clean_case_with_category_is_contradictory(self):
        case = make_case(defect=False)
        case["ground_truth"]["category"] = "logic-error"
        self.assert_rejected(case, "clean case must not carry")

    def test_affected_files_must_match_diff_both_ways(self):
        listed_extra = make_case(affected_files=["src/app.py", "src/ghost.py"])
        self.assert_rejected(listed_extra, "not present in diff")
        missing_listed = make_case(affected_files=["src/app.py"])
        missing_listed["diff"] = missing_listed["diff"] + [
            "--- a/src/other.py", "+++ b/src/other.py",
            "@@ -1 +1 @@", "-a", "+b"]
        self.assert_rejected(missing_listed, "missing from affected_files")

    def test_secret_shaped_string_rejected(self):
        case = make_case()
        # Assembled at runtime so the fake key never exists contiguously
        # in this file — forge-side secret scanners (rightly) can't tell a
        # test fixture from a leak.
        fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"
        case["diff"].append(f"+key = \"{fake_key}\"")
        self.assert_rejected(case, "secret pattern")

    def test_private_path_rejected(self):
        case = make_case()
        case["diff"].append("+path = \"/home/someone/data\"")
        self.assert_rejected(case, "private-content")


class LoadCorpusTests(unittest.TestCase):
    def test_id_must_match_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case("real-name")
            with open(os.path.join(tmp, "other-name.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(case, fh)
            with self.assertRaisesRegex(ConfigError, "does not match filename"):
                corpus.load_corpus(tmp)

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case("dup")
            write_corpus(tmp, case)
            other = copy.deepcopy(case)
            with open(os.path.join(tmp, "dup2.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(other, fh)
            with self.assertRaises(ConfigError):
                corpus.load_corpus(tmp)

    def test_near_duplicate_diffs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = make_case("case-a")
            b = make_case("case-b")
            # Same diff content as a, differing only in whitespace on a
            # content line (file markers untouched).
            b["diff"] = a["diff"][:-1] + [a["diff"][-1] + "   "]
            write_corpus(tmp, a, b)
            with self.assertRaisesRegex(ConfigError, "near-duplicate"):
                corpus.load_corpus(tmp)

    def test_empty_directory_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                corpus.load_corpus(tmp)

    def test_diff_list_normalized_to_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_corpus(tmp, make_case("norm-me"))
            cases = corpus.load_corpus(tmp)
        self.assertIsInstance(cases[0]["diff"], str)
        self.assertIn("+new_norm-me", cases[0]["diff"])

    def test_summarize_distributions(self):
        cases = [make_case("a1"), make_case("b2", defect=False),
                 make_case("c3", language="go")]
        summary = corpus.summarize(cases)
        self.assertEqual(summary["cases"], 3)
        self.assertEqual(summary["defective"], 2)
        self.assertEqual(summary["clean"], 1)
        self.assertEqual(summary["languages"], {"go": 1, "python": 2})
        self.assertEqual(summary["author_families"], {"claude": 3})
        self.assertEqual(summary["severities"],
                         {"(clean)": 1, "medium-high": 2})

    def test_fingerprint_is_content_addressed_and_order_independent(self):
        a, b = make_case("fp-a"), make_case("fp-b")
        self.assertEqual(corpus.corpus_fingerprint([a, b]),
                         corpus.corpus_fingerprint([b, a]))
        changed = copy.deepcopy(a)
        changed["title"] = "different title"
        self.assertNotEqual(corpus.corpus_fingerprint([a, b]),
                            corpus.corpus_fingerprint([changed, b]))


class RealCorpusTests(unittest.TestCase):
    """Guards over the corpus actually shipped in eval/cases."""

    def test_shipped_corpus_is_valid(self):
        cases = corpus.load_corpus(corpus.DEFAULT_CASES_DIR)
        summary = corpus.summarize(cases)
        self.assertEqual(summary["cases"], 53)
        self.assertEqual(summary["defective"], 41)
        self.assertEqual(summary["clean"], 12)
        # The methodology's pilot floor: at least five real programming
        # languages, and enough clean controls for precision to mean
        # something.
        programming = set(summary["languages"]) - {"config", "docs"}
        self.assertGreaterEqual(len(programming), 5)
        self.assertGreaterEqual(summary["clean"] / summary["cases"], 0.2)
        self.assertGreaterEqual(summary["cross_file_cases"], 4)
        # Self-authorship is a documented limitation and must stay
        # machine-readable, not implicit.
        self.assertIn("claude", summary["author_families"])

    def test_cli_validates_shipped_corpus(self):
        self.assertEqual(corpus.main(["--cases", corpus.DEFAULT_CASES_DIR]), 0)


if __name__ == "__main__":
    unittest.main()
