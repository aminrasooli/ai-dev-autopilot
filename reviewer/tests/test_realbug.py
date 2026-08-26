"""Real-bug candidate queue tests (M4). The invariant under test: the
license/safety gate actually blocks a candidate — this is a queue that
must be able to say no, not one that only ever holds pre-approved-looking
entries."""

import json
import os
import tempfile
import unittest

from reviewer import realbug


def make_candidate(candidate_id="widget-fix", **overrides):
    obj = {
        "candidate_id": candidate_id,
        "repository": "example/widget",
        "repository_url": "https://github.com/example/widget",
        "commit": "abc1234",
        "parent_commit": "def5678",
        "language": "python",
        "changed_files": ["widget/core.py"],
        "diff_size_lines": 12,
        "license": "MIT",
        "bugfix_confidence": 0.8,
        "incorporation_safe": True,
        "recommended_treatment": "transformed",
        "status": "candidate",
        "notes": "a plausible off-by-one fix with a regression test",
    }
    obj.update(overrides)
    return obj


def write_queue(tmp, *candidates):
    for c in candidates:
        with open(os.path.join(tmp, c["candidate_id"] + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump(c, fh)


class ValidateCandidateTests(unittest.TestCase):
    def assert_rejected(self, candidate, fragment):
        errors, _ = realbug.validate_candidate(candidate)
        self.assertTrue(any(fragment in e for e in errors),
                        f"expected error containing {fragment!r}, got {errors}")

    def test_valid_candidate_passes(self):
        errors, warnings = realbug.validate_candidate(make_candidate())
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_required_field(self):
        c = make_candidate()
        del c["license"]
        self.assert_rejected(c, "missing 'license'")

    def test_unknown_field_rejected(self):
        self.assert_rejected(make_candidate(surprise=True), "unknown fields")

    def test_bad_candidate_id_rejected(self):
        self.assert_rejected(make_candidate(candidate_id="Not Kebab"),
                             "candidate_id must be kebab-case")

    def test_bad_repository_shape_rejected(self):
        self.assert_rejected(make_candidate(repository="not-a-repo"),
                             "repository must look like")

    def test_repository_url_must_be_https(self):
        self.assert_rejected(
            make_candidate(repository_url="http://github.com/example/widget"),
            "repository_url must be an https")

    def test_commit_must_be_hex_sha(self):
        self.assert_rejected(make_candidate(commit="not-hex!"),
                             "must be a 7-40 char hex commit sha")

    def test_commit_and_parent_must_differ(self):
        self.assert_rejected(make_candidate(parent_commit="abc1234"),
                             "must differ")

    def test_diff_size_must_be_positive_int(self):
        self.assert_rejected(make_candidate(diff_size_lines=0),
                             "positive integer")
        self.assert_rejected(make_candidate(diff_size_lines=1.5),
                             "positive integer")

    def test_confidence_must_be_in_range(self):
        self.assert_rejected(make_candidate(bugfix_confidence=1.5),
                             "0.0-1.0")

    def test_bad_treatment_rejected(self):
        self.assert_rejected(make_candidate(recommended_treatment="copy-paste"),
                             "recommended_treatment")

    def test_bad_status_rejected(self):
        self.assert_rejected(make_candidate(status="approved"), "status")

    def test_empty_notes_rejected(self):
        self.assert_rejected(make_candidate(notes=""), "notes must explain")

    # The actual license/safety gate.

    def test_gpl_license_forces_reject_or_synthetic(self):
        c = make_candidate(license="GPL-3.0", recommended_treatment="transformed")
        self.assert_rejected(c, "is not permissive")

    def test_gpl_license_with_reject_passes(self):
        c = make_candidate(license="GPL-3.0", recommended_treatment="reject",
                           incorporation_safe=False, status="rejected")
        errors, _ = realbug.validate_candidate(c)
        self.assertEqual(errors, [])

    def test_gpl_license_with_synthetic_reconstruction_passes(self):
        c = make_candidate(license="GPL-3.0",
                           recommended_treatment="synthetic-reconstruction")
        errors, _ = realbug.validate_candidate(c)
        self.assertEqual(errors, [])

    def test_incorporation_unsafe_forces_reject(self):
        c = make_candidate(incorporation_safe=False,
                           recommended_treatment="transformed")
        self.assert_rejected(c, "requires recommended_treatment 'reject'")

    def test_verbatim_requires_permissive_license(self):
        c = make_candidate(license="MPL-2.0", recommended_treatment="verbatim")
        self.assert_rejected(c, "'verbatim' requires a known-permissive license")

    def test_verbatim_with_permissive_license_passes(self):
        c = make_candidate(license="BSD-3-Clause", recommended_treatment="verbatim")
        errors, _ = realbug.validate_candidate(c)
        self.assertEqual(errors, [])

    def test_unrecognized_license_warns_not_errors(self):
        c = make_candidate(license="SomeUnusualLicense-1.0")
        errors, warnings = realbug.validate_candidate(c)
        self.assertEqual(errors, [])
        self.assertTrue(any("needs a human license read" in w for w in warnings))


class LoadQueueTests(unittest.TestCase):
    def test_valid_queue_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_queue(tmp, make_candidate("a-fix"), make_candidate("b-fix"))
            candidates, errors, warnings = realbug.load_queue(tmp, collect=True)
            self.assertEqual(errors, [])
            self.assertEqual(len(candidates), 2)

    def test_id_must_match_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = make_candidate("a-fix")
            with open(os.path.join(tmp, "b-fix.json"), "w", encoding="utf-8") as fh:
                json.dump(c, fh)
            _, errors, _ = realbug.load_queue(tmp, collect=True)
            self.assertTrue(any("does not match filename" in e for e in errors))

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_queue(tmp, make_candidate("a-fix"))
            with open(os.path.join(tmp, "a-fix-2.json"), "w", encoding="utf-8") as fh:
                json.dump(make_candidate("a-fix"), fh)
            _, errors, _ = realbug.load_queue(tmp, collect=True)
            self.assertTrue(any("duplicate candidate_id" in e for e in errors))

    def test_summarize_counts_reject_and_verbatim(self):
        candidates = [
            make_candidate("a-fix"),
            make_candidate("b-fix", license="GPL-3.0",
                          recommended_treatment="reject",
                          incorporation_safe=False, status="rejected"),
            make_candidate("c-fix", recommended_treatment="verbatim"),
        ]
        summary = realbug.summarize(candidates)
        self.assertEqual(summary["candidates"], 3)
        self.assertEqual(summary["reject_count"], 1)
        self.assertEqual(summary["verbatim_count"], 1)


class ShippedQueueTests(unittest.TestCase):
    """The real queue this session populated must itself be valid."""

    def test_shipped_queue_is_valid(self):
        directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "eval", "realbug-queue")
        candidates, errors, warnings = realbug.load_queue(directory, collect=True)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(candidates), 1)

    def test_shipped_queue_contains_at_least_one_rejected_candidate(self):
        directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "eval", "realbug-queue")
        candidates = realbug.load_queue(directory)
        self.assertTrue(any(c["recommended_treatment"] == "reject"
                            for c in candidates),
                        "the queue should demonstrate the license gate can "
                        "actually reject a candidate, not only accept them")


if __name__ == "__main__":
    unittest.main()
