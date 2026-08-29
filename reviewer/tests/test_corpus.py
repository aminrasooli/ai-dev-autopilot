"""Schema-v2 and corpus-validator tests. Fully offline, like everything
in this suite."""

import copy
import hashlib
import json
import os
import re
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
    if defect:
        obj["difficulty"] = "moderate"
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

    def _mined_provenance(self, **overrides):
        prov = {
            "type": "mined-real-fix", "author_family": "human",
            "human_authored": False, "reference": "https://example.com/c/abc123f",
            "source_repository": "example/widget", "source_commit": "abc123f",
            "source_license": "MIT", "transformation": "transformed",
        }
        prov.update(overrides)
        return prov

    def test_mined_real_fix_full_provenance_passes(self):
        case = make_case(provenance=self._mined_provenance())
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_mined_real_fix_requires_source_repository(self):
        prov = self._mined_provenance()
        del prov["source_repository"]
        self.assert_rejected(make_case(provenance=prov),
                             "requires provenance.source_repository")

    def test_mined_real_fix_requires_source_commit(self):
        prov = self._mined_provenance()
        del prov["source_commit"]
        self.assert_rejected(make_case(provenance=prov),
                             "requires provenance.source_commit")

    def test_mined_real_fix_requires_source_license(self):
        prov = self._mined_provenance()
        del prov["source_license"]
        self.assert_rejected(make_case(provenance=prov),
                             "requires provenance.source_license")

    def test_mined_real_fix_requires_transformation(self):
        prov = self._mined_provenance()
        del prov["transformation"]
        self.assert_rejected(make_case(provenance=prov),
                             "requires provenance.transformation")

    def test_bad_transformation_value_rejected(self):
        prov = self._mined_provenance(transformation="mostly-copied")
        self.assert_rejected(make_case(provenance=prov),
                             "provenance.transformation")

    def test_transformation_outside_mined_real_fix_rejected(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "claude",
            "transformation": "verbatim"})
        self.assert_rejected(case, "only applies to provenance.type mined-real-fix")

    def test_empty_string_provenance_field_rejected(self):
        prov = self._mined_provenance(source_license="")
        self.assert_rejected(make_case(provenance=prov),
                             "provenance.source_license must be a non-empty string")

    def test_human_family_requires_explicit_human_authored(self):
        case = make_case(provenance={"type": "seeded-synthetic",
                                     "author_family": "human"})
        self.assert_rejected(case, "requires an explicit provenance.human_authored")

    def test_human_authored_false_is_the_human_reviewed_case(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "human",
            "human_authored": False})
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_human_authored_true_requires_human_family(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "claude",
            "human_authored": True})
        self.assert_rejected(case, "requires author_family 'human'")

    def test_human_authored_must_be_boolean(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "human",
            "human_authored": "yes"})
        self.assert_rejected(case, "provenance.human_authored must be a boolean")

    def test_author_model_recorded_for_non_claude_family(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "qwen",
            "author_model": "qwen3.6:27b"})
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_deepseek_is_a_known_author_family(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "deepseek",
            "author_model": "deepseek-r1:14b"})
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    # --- adversarial provenance: claims the schema must refuse -------
    # Each of these validated before the M4 review pass. They are the
    # shapes that would let a published claim ("human-written",
    # "Qwen-authored", "license-checked real bug") be false while the
    # corpus validated clean.

    def test_verbatim_incorporation_requires_permissive_license(self):
        prov = self._mined_provenance(source_license="GPL-3.0",
                                      transformation="verbatim")
        self.assert_rejected(make_case(provenance=prov),
                             "requires a known-permissive source_license")

    def test_transformed_incorporation_requires_permissive_license(self):
        prov = self._mined_provenance(source_license="proprietary",
                                      transformation="transformed")
        self.assert_rejected(make_case(provenance=prov),
                             "requires a known-permissive source_license")

    def test_unrecognized_license_string_is_not_treated_as_permissive(self):
        prov = self._mined_provenance(source_license="looks fine to me",
                                      transformation="verbatim")
        self.assert_rejected(make_case(provenance=prov),
                             "requires a known-permissive source_license")

    def test_copyleft_transformed_rejected_on_the_real_admission_path(self):
        # The advisory queue (reviewer.realbug) already refuses this, but
        # the queue is not what admits a case — validate_case is. The
        # queue's own GPL reject-demo candidate must therefore also fail
        # here, or a copyleft case could reach a scored corpus by
        # skipping the queue entirely (docs/M4_DESIGN_BRIEF.md §A rule 1).
        prov = self._mined_provenance(source_license="GPL-2.0-only",
                                      transformation="transformed")
        self.assert_rejected(make_case(provenance=prov),
                             "requires a known-permissive source_license")

    def test_synthetic_reconstruction_is_exempt_from_the_license_gate(self):
        # No code is derived, so a copyleft source is not a problem —
        # the attribution is still recorded (docs/M4_DESIGN_BRIEF.md §A).
        prov = self._mined_provenance(source_license="GPL-2.0-only",
                                      transformation="synthetic-reconstruction")
        errors, _ = corpus.validate_case(make_case(provenance=prov))
        self.assertEqual(errors, [])

    def test_source_commit_must_be_a_real_looking_sha(self):
        prov = self._mined_provenance(source_commit="trust me")
        self.assert_rejected(make_case(provenance=prov),
                             "7-40 char hex commit sha")

    def test_source_attribution_without_a_license_rejected(self):
        case = make_case(provenance={
            "type": "authored-realistic", "author_family": "claude",
            "source_repository": "pallets/flask",
            "source_commit": "05e9c6bd630ecf4ec0ec884b1fc7901663737bc7"})
        self.assert_rejected(case, "without provenance.source_license")

    def test_human_authored_true_cannot_name_an_author_model(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "human",
            "human_authored": True, "author_model": "qwen3.6:27b"})
        self.assert_rejected(case, "cannot carry provenance.author_model")

    def test_author_family_and_author_model_must_agree(self):
        # ROADMAP §9 failure mode 3: a case Claude actually wrote must
        # not be able to sit behind a Qwen label.
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "qwen",
            "author_model": "claude-sonnet-5"})
        self.assert_rejected(case, "does not name a 'qwen' model")

    def test_claude_family_cannot_name_a_local_model(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "claude",
            "author_model": "deepseek-r1:14b"})
        self.assert_rejected(case, "does not name a 'claude' model")

    def test_mixed_family_may_name_any_model(self):
        # 'mixed' is the honest label when more than one author touched
        # the content, so it carries no family/model agreement rule.
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "mixed",
            "author_model": "claude-opus-5",
            "provenance_notes": "qwen drafted, claude repaired the diff"})
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_human_reviewed_case_may_name_the_formatting_model(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "human",
            "human_authored": False, "author_model": "claude-opus-5"})
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_unknown_provenance_field_rejected(self):
        case = make_case(provenance={
            "type": "seeded-synthetic", "author_family": "claude",
            "surprise": True})
        self.assert_rejected(case, "unknown provenance fields")

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

    def test_defective_case_must_declare_difficulty(self):
        case = make_case()
        del case["difficulty"]
        self.assert_rejected(case, "must declare a difficulty")

    def test_unknown_difficulty_rejected(self):
        self.assert_rejected(make_case(difficulty="trivial"), "difficulty")

    def test_clean_case_may_declare_difficulty(self):
        case = make_case(defect=False)
        case["difficulty"] = "subtle"
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_clean_case_difficulty_still_checked_against_vocabulary(self):
        case = make_case(defect=False)
        case["difficulty"] = "trivial"
        self.assert_rejected(case, "difficulty")

    def test_execution_validated_true_requires_note(self):
        case = make_case()
        case["ground_truth"]["execution_validated"] = True
        self.assert_rejected(case, "requires a non-empty ground_truth.validation_note")

    def test_execution_validated_with_note_passes(self):
        case = make_case()
        case["ground_truth"]["execution_validated"] = True
        case["ground_truth"]["validation_note"] = (
            "ran a 4-goroutine race harness 200x offline, race manifested "
            "in 37/200 runs")
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_execution_validated_on_clean_case_passes(self):
        case = make_case(defect=False)
        case["ground_truth"]["execution_validated"] = True
        case["ground_truth"]["validation_note"] = "ran offline, no race observed"
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_execution_validated_must_be_boolean(self):
        case = make_case()
        case["ground_truth"]["execution_validated"] = "yes"
        self.assert_rejected(case, "execution_validated")

    def test_validation_artifact_sha256_bad_format_rejected(self):
        case = make_case()
        case["ground_truth"]["execution_validated"] = True
        case["ground_truth"]["validation_note"] = "note"
        case["ground_truth"]["validation_artifact_sha256"] = "not-a-hash"
        self.assert_rejected(case, "validation_artifact_sha256")

    def test_validation_artifact_sha256_valid_format_passes(self):
        case = make_case()
        case["ground_truth"]["execution_validated"] = True
        case["ground_truth"]["validation_note"] = "note"
        case["ground_truth"]["validation_artifact_sha256"] = "a" * 64
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_still_unknown_ground_truth_field_rejected(self):
        case = make_case()
        case["ground_truth"]["vibes_check"] = True
        self.assert_rejected(case, "unknown ground_truth fields")

    def test_accepted_categories_accepts_valid_alternative(self):
        case = make_case()
        case["ground_truth"]["accepted_categories"] = ["concurrency"]
        errors, _ = corpus.validate_case(case)
        self.assertEqual(errors, [])

    def test_accepted_categories_rejects_off_vocabulary(self):
        case = make_case()
        case["ground_truth"]["accepted_categories"] = ["vibes"]
        self.assert_rejected(case, "accepted_categories entry")

    def test_accepted_categories_rejects_repeating_the_primary(self):
        case = make_case()
        case["ground_truth"]["accepted_categories"] = ["logic-error"]
        self.assert_rejected(case, "repeats the primary")

    def test_accepted_categories_are_capped(self):
        # Alternatives must stay rare: an unbounded list would make
        # category correctness meaningless.
        case = make_case()
        case["ground_truth"]["accepted_categories"] = [
            "concurrency", "api-misuse", "resource-leak"]
        self.assert_rejected(case, "at most 2")

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

    def test_cross_corpus_duplicate_id_detected(self):
        # Every corpus lives in its own directory, so load_corpus's
        # within-directory dedup cannot see a tranche re-admitting a case
        # that already exists in a frozen corpus.
        a = make_case("shared-id")
        b = copy.deepcopy(a)
        b["diff"] = ["--- a/src/app.py", "+++ b/src/app.py",
                     "@@ -1,2 +1,2 @@", "-wholly", "+different"]
        conflicts = corpus.cross_corpus_conflicts({"v2": [a], "tranche": [b]})
        kinds = {c["kind"] for c in conflicts}
        self.assertIn("duplicate-id", kinds)

    def test_cross_corpus_duplicate_diff_detected(self):
        a = make_case("case-one")
        b = make_case("case-two")
        b["diff"] = a["diff"]
        conflicts = corpus.cross_corpus_conflicts({"v2": [a], "tranche": [b]})
        self.assertEqual([c["kind"] for c in conflicts], ["duplicate-diff"])

    def test_cross_corpus_distinct_corpora_have_no_conflicts(self):
        # The check must not fire on genuinely different corpora, or it
        # would be noise the moment a real tranche lands.
        conflicts = corpus.cross_corpus_conflicts(
            {"v2": [make_case("alpha"), make_case("beta")],
             "tranche": [make_case("gamma")]})
        self.assertEqual(conflicts, [])

    def test_cross_corpus_check_runs_over_the_shipped_corpora(self):
        # The real invariant this protects: the corpora actually shipped
        # in this repository do not collide with each other. Enumerated by
        # discovery, not by name — when eval/cases-provenance landed, the
        # hand-written v2/v3 version of this test kept passing while
        # covering two of the three corpora it claimed to cover.
        corpora = {name: corpus.load_corpus(path) for name, path
                   in corpus.shipped_corpus_dirs().items()}
        self.assertGreaterEqual(len(corpora), 3)
        self.assertEqual(corpus.cross_corpus_conflicts(corpora), [])

    def test_shipped_corpus_discovery_finds_every_corpus(self):
        # Guards the convention discovery relies on. If a future tranche
        # is laid out differently, this fails loudly here rather than
        # silently shrinking the cross-corpus and contamination checks.
        found = corpus.shipped_corpus_dirs()
        self.assertEqual(sorted(found),
                         ["cases", "cases-provenance", "cases-v3"])
        for path in found.values():
            self.assertTrue(os.path.isdir(path))
            self.assertTrue(corpus.load_corpus(path))

    def test_shipped_corpus_discovery_skips_a_contentless_directory(self):
        # Scaffolding a tranche must not break callers before it has
        # cases in it.
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "eval", "cases-empty", "cases"))
            real = os.path.join(root, "eval", "cases")
            os.makedirs(real)
            write_corpus(real, make_case("only-one"))
            self.assertEqual(sorted(corpus.shipped_corpus_dirs(root)), ["cases"])

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

    def test_rendered_summary_prints_the_fingerprint(self):
        # README.md's reproduction path tells a stranger that
        # `bin/review-corpus --cases ...` prints the corpus fingerprint,
        # and that comparing it is what step 2 establishes. Emitting it
        # only under --json made that instruction false, so the claim is
        # pinned here rather than left to prose.
        cases = [make_case("fp-a"), make_case("fp-b", defect=False)]
        summary = corpus.summarize(cases)
        rendered = corpus.render_summary(summary)
        self.assertIn(summary["sha256"], rendered)
        self.assertIn("fingerprint", rendered)

    def test_summarize_counts_execution_validated_cases(self):
        a = make_case("ev-a")
        a["ground_truth"]["execution_validated"] = True
        a["ground_truth"]["validation_note"] = "offline race harness"
        b = make_case("ev-b")
        summary = corpus.summarize([a, b])
        self.assertEqual(summary["execution_validated_cases"], 1)

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
        self.assertEqual(summary["cases"], 54)
        self.assertEqual(summary["defective"], 40)
        self.assertEqual(summary["clean"], 14)
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

    def test_frozen_corpus_fingerprints_are_exact(self):
        # v2 and v3 are declared immutable after freeze
        # (eval/cases-v3/README.md, CURRENT-MILESTONE.md): every
        # authoritative M1/M2/M3 result names one of these two hashes, so
        # a single edited byte in either corpus silently invalidates
        # published evidence. Pin them here so that edit fails a test
        # instead of being discovered at citation time. These values are
        # never "updated to match" — a genuine corpus change requires a
        # new fingerprint and new experiments, not a new assertion.
        eval_dir = os.path.dirname(corpus.DEFAULT_CASES_DIR)
        frozen = {
            corpus.DEFAULT_CASES_DIR:
                "f31d46310988f61c4534344ad05a52a4385fd151"
                "59126a0be85aad532f045690",
            os.path.join(eval_dir, "cases-v3", "cases"):
                "81daa0b7a48259184a91c48ab1dcf17c9d3ed490"
                "2fa891b5895db0f29fd79790",
        }
        for path, expected in frozen.items():
            actual = corpus.corpus_fingerprint(corpus.load_corpus(path))
            self.assertEqual(actual, expected,
                             f"frozen corpus {path} changed fingerprint")

    def test_documented_provenance_fingerprint_matches_the_corpus(self):
        # The provenance corpus is deliberately NOT frozen — it grows as
        # tranches land — so it cannot be pinned to a constant the way v2
        # and v3 are above. But its fingerprint is *published* in
        # eval/cases-provenance/README.md, and a published fingerprint
        # that no longer matches the corpus is worse than none: it is the
        # value a reader would cite to prove which corpus a result ran
        # against. This drifted once already, when case content was
        # edited after the fingerprint was written down. Assert the
        # documented value against the computed one so the doc must be
        # updated in the same commit as the corpus, rather than silently
        # going stale. Unlike the frozen test above, updating this
        # expected value IS the correct fix when the corpus legitimately
        # changes.
        eval_dir = os.path.dirname(corpus.DEFAULT_CASES_DIR)
        cases = os.path.join(eval_dir, "cases-provenance", "cases")
        readme = os.path.join(eval_dir, "cases-provenance", "README.md")
        if not os.path.isdir(cases):
            self.skipTest("provenance corpus not present")
        actual = corpus.corpus_fingerprint(corpus.load_corpus(cases))
        with open(readme, encoding="utf-8") as handle:
            text = handle.read()
        # assertTrue, not assertIn: assertIn would dump the whole README
        # into the failure output and bury the one line that matters.
        self.assertTrue(
            actual in text,
            "eval/cases-provenance/README.md does not record the provenance "
            f"corpus's current fingerprint.\n  computed: {actual}\n"
            "  fix: update the fingerprint row in that README in the same "
            "commit that changes the corpus.")

    def test_cli_validates_shipped_corpus(self):
        self.assertEqual(corpus.main(["--cases", corpus.DEFAULT_CASES_DIR]), 0)


if __name__ == "__main__":
    unittest.main()


class DiagnosticsTests(unittest.TestCase):
    def test_similarity_flags_near_duplicates_but_not_distinct_cases(self):
        from reviewer import diagnose
        body = ("-    total = compute_running_total(order.items, tax_rate)\n"
                "-    return Invoice(order_id=order.id, total=total)\n"
                "+    total = compute_running_total(order.items)\n"
                "+    return Invoice(order_id=order.id, total=total)\n")
        a = make_case("sim-a")
        a["diff"] = "--- a/src/a.py\n+++ b/src/a.py\n@@ -1,4 +1,4 @@\n" + body
        b = make_case("sim-b")   # same change, different file
        b["diff"] = "--- a/src/b.py\n+++ b/src/b.py\n@@ -1,4 +1,4 @@\n" + body
        flags = diagnose.similarity_report([a, b], threshold=0.3)
        self.assertTrue(flags, "identical changed bodies must be flagged")
        self.assertGreater(flags[0]["jaccard"], 0.9)

        c = make_case("sim-c")
        c["diff"] = ("--- a/src/c.py\n+++ b/src/c.py\n@@ -1,3 +1,3 @@\n"
                     "-    session_token = build_bearer_header(user_secret)\n"
                     "+    session_token = build_bearer_header(user_secret, ttl)\n")
        self.assertEqual(diagnose.similarity_report([a, c], threshold=0.3), [],
                         "unrelated changes must not be flagged")

    def test_jaccard_bounds(self):
        from reviewer import diagnose
        s = diagnose.shingles("alpha beta gamma delta epsilon zeta")
        self.assertEqual(diagnose.jaccard(s, s), 1.0)
        self.assertEqual(diagnose.jaccard(s, set()), 0.0)

    def test_context_budget_reports_real_prompt_size(self):
        from reviewer import diagnose
        case = make_case("ctx")
        case["diff"] = "\n".join(case["diff"]) + "\n"
        cb = diagnose.context_budget([case])
        # The measured size must be the full prompt, not just the diff.
        self.assertGreater(cb["prompt_chars"]["min"], len(case["diff"]))
        self.assertEqual(cb["diff_lines"]["min"], len(case["diff"].splitlines()))

    def test_diagnose_over_the_real_corpus_has_no_composite_score(self):
        from reviewer import diagnose, corpus as corpus_mod
        d = diagnose.diagnose(corpus_mod.load_corpus(corpus_mod.DEFAULT_CASES_DIR))
        self.assertEqual(d["cases"], 54)
        blob = json.dumps(d).lower()
        for banned in ("quality_score", "overall_score", "composite"):
            self.assertNotIn(banned, blob)


class PublishedEvidenceIntegrityTests(unittest.TestCase):
    """`eval/EXPERIMENTS.md` records a sha256 for each authoritative
    result file. Nothing checked it, so a published result could be
    edited — by accident, a bad merge, or deliberately — and every
    citation of it would keep reading as valid. These are the numbers the
    project's public claims rest on, so the recorded hash is checked
    against the file it names."""

    _RECORD = re.compile(
        r"`(?P<name>[A-Za-z0-9._-]+\.json)` \(sha256 "
        r"`(?P<prefix>[0-9a-f]{6,})…(?P<suffix>[0-9a-f]{4,})`\)")

    def _repo_root(self):
        return os.path.dirname(os.path.dirname(corpus.DEFAULT_CASES_DIR))

    def test_recorded_result_hashes_match_the_files(self):
        root = self._repo_root()
        experiments = os.path.join(root, "eval", "EXPERIMENTS.md")
        if not os.path.exists(experiments):
            self.skipTest("EXPERIMENTS.md not present")
        with open(experiments, encoding="utf-8") as handle:
            text = handle.read()

        records = list(self._RECORD.finditer(text))
        self.assertTrue(records,
                        "EXPERIMENTS.md records no result hashes — if the "
                        "format changed, update this test rather than "
                        "dropping the check")

        for match in records:
            name = match.group("name")
            path = os.path.join(root, "eval", "results", name)
            with self.subTest(result=name):
                self.assertTrue(os.path.exists(path),
                                f"{name} is cited in EXPERIMENTS.md but "
                                "missing from eval/results/")
                digest = hashlib.sha256()
                with open(path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(65536), b""):
                        digest.update(chunk)
                actual = digest.hexdigest()
                self.assertTrue(
                    actual.startswith(match.group("prefix"))
                    and actual.endswith(match.group("suffix")),
                    f"{name} no longer matches the sha256 recorded in "
                    f"EXPERIMENTS.md\n  recorded: {match.group('prefix')}…"
                    f"{match.group('suffix')}\n  actual:   {actual}\n"
                    "A published result must not change. If this file was "
                    "legitimately regenerated it is a NEW experiment with a "
                    "new row, not an edit to this one.")

    def test_every_authoritative_result_still_verifies(self):
        # A result whose summary no longer follows from its own runs must
        # never keep being cited. reviewer.verify is the same check
        # SUBMIT.md asks outside submitters to run on themselves.
        from reviewer import verify as verify_mod
        results = os.path.join(self._repo_root(), "eval", "results")
        if not os.path.isdir(results):
            self.skipTest("eval/results not present")
        reports = [f for f in sorted(os.listdir(results))
                   if f.endswith("-3runs.json") and "checkpoint" not in f]
        self.assertTrue(reports, "no authoritative result files found")
        for name in reports:
            with self.subTest(result=name):
                with open(os.path.join(results, name), encoding="utf-8") as fh:
                    report = json.load(fh)
                errors, _ = verify_mod.verify_report(report, origin=name)
                self.assertEqual(errors, [], f"{name} is not internally consistent")
