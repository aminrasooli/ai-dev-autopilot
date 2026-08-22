"""Case-proposal and independent-audit intake tests.

The invariant under test throughout: a model may propose, but nothing
here can write into the scored corpus.
"""

import json
import os
import tempfile
import unittest

from reviewer import propose

from .test_corpus import make_case


def make_proposal(pid="p1", family="qwen", **overrides):
    case = make_case("proposed-" + pid)
    case["provenance"]["author_family"] = family
    obj = {
        "proposal_id": pid,
        "author_family": family,
        "generator": "qwen3.6:27b",
        "status": "proposed",
        "case": case,
        "rationale": "covers a category the corpus is thin on",
    }
    obj.update(overrides)
    return obj


def make_audit(**overrides):
    obj = {
        "case_id": "01-obvious-off-by-one",
        "defect_opinion": "defect",
        "confidence": 0.9,
        "rationale": "the loop bound exceeds the slice length",
        "category_opinion": "logic-error",
        "severity_opinion": "high",
        "disagrees_with_ground_truth": False,
    }
    obj.update(overrides)
    return obj


class ProposalTests(unittest.TestCase):
    def assert_rejected(self, obj, fragment):
        errors, _ = propose.validate_proposal(obj)
        self.assertTrue(any(fragment in e for e in errors),
                        f"expected {fragment!r}, got {errors}")

    def test_valid_proposal(self):
        errors, _ = propose.validate_proposal(make_proposal())
        self.assertEqual(errors, [])

    def test_embedded_case_must_satisfy_the_real_schema(self):
        # A proposal that could not become a case is not a useful proposal.
        p = make_proposal()
        p["case"]["language"] = "cobol"
        self.assert_rejected(p, "language")

    def test_author_family_must_match_the_embedded_case(self):
        p = make_proposal()
        p["case"]["provenance"]["author_family"] = "claude"
        self.assert_rejected(p, "disagrees with the proposal")

    def test_generator_must_be_named(self):
        self.assert_rejected(make_proposal(generator="  "), "generator must name")

    def test_unknown_status_rejected(self):
        self.assert_rejected(make_proposal(status="merged"), "status")

    def test_accepted_status_is_only_advisory(self):
        _, warnings = propose.validate_proposal(make_proposal(status="accepted"))
        self.assertTrue(any("advisory only" in w for w in warnings))

    def test_load_directory_and_reject_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, pid in (("a.json", "p1"), ("b.json", "p2")):
                with open(os.path.join(tmp, name), "w", encoding="utf-8") as fh:
                    json.dump(make_proposal(pid), fh)
            items, errors, _ = propose.load_proposals(tmp)
            self.assertEqual(len(items), 2)
            self.assertEqual(errors, [])
            with open(os.path.join(tmp, "c.json"), "w", encoding="utf-8") as fh:
                json.dump(make_proposal("p1"), fh)
            _, errors, _ = propose.load_proposals(tmp)
            self.assertTrue(any("duplicate proposal_id" in e for e in errors))

    def test_proposals_never_touch_the_scored_corpus(self):
        from reviewer.corpus import DEFAULT_CASES_DIR
        before = sorted(os.listdir(DEFAULT_CASES_DIR))
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "a.json"), "w", encoding="utf-8") as fh:
                json.dump(make_proposal(), fh)
            propose.load_proposals(tmp)
        self.assertEqual(sorted(os.listdir(DEFAULT_CASES_DIR)), before)


class AuditTests(unittest.TestCase):
    def assert_rejected(self, obj, fragment):
        errors, _ = propose.validate_audit(obj)
        self.assertTrue(any(fragment in e for e in errors),
                        f"expected {fragment!r}, got {errors}")

    def test_valid_audit(self):
        errors, _ = propose.validate_audit(make_audit())
        self.assertEqual(errors, [])

    def test_confidence_bounds(self):
        self.assert_rejected(make_audit(confidence=1.5), "confidence")
        self.assert_rejected(make_audit(confidence="high"), "confidence")

    def test_off_vocabulary_opinions_rejected(self):
        self.assert_rejected(make_audit(category_opinion="vibes"), "category_opinion")
        self.assert_rejected(make_audit(severity_opinion="catastrophic"),
                             "severity_opinion")

    def test_clean_opinion_must_not_carry_a_category(self):
        self.assert_rejected(
            make_audit(defect_opinion="clean"), "must not carry a category")

    def test_unsure_is_allowed(self):
        errors, _ = propose.validate_audit(
            make_audit(defect_opinion="unsure", category_opinion=None,
                       severity_opinion=None))
        self.assertEqual(errors, [])

    def test_load_audits_flags_unknown_case_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audits.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"audits": [make_audit(case_id="not-a-real-case")]}, fh)
            items, errors, warnings = propose.load_audits(
                path, known_case_ids={"01-obvious-off-by-one"})
        self.assertEqual(errors, [])
        self.assertEqual(len(items), 1)
        self.assertTrue(any("unknown case" in w for w in warnings))

    def test_bare_list_form_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "audits.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([make_audit()], fh)
            items, errors, _ = propose.load_audits(path)
        self.assertEqual(errors, [])
        self.assertEqual(len(items), 1)


if __name__ == "__main__":
    unittest.main()
