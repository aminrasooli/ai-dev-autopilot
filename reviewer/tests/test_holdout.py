"""Private holdout contamination-check tests (M4-D). The invariant under
test: a holdout directory that collides with (or is already named in) a
public record is flagged, not silently treated as private."""

import os
import tempfile
import unittest

from reviewer import holdout

from .test_corpus import make_case, write_corpus


class CheckHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.repo_root.name, "eval", "cases"))
        os.makedirs(os.path.join(self.repo_root.name, "eval", "cases-v3", "cases"))
        write_corpus(os.path.join(self.repo_root.name, "eval", "cases"),
                    make_case("public-1"), make_case("public-2", defect=False))
        with open(os.path.join(self.repo_root.name, "eval", "EXPERIMENTS.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("no fingerprints referenced yet\n")

    def tearDown(self):
        self.repo_root.cleanup()

    def test_disjoint_holdout_is_clean(self):
        with tempfile.TemporaryDirectory() as holdout_dir:
            write_corpus(holdout_dir, make_case("private-1"),
                        make_case("private-2", defect=False))
            report = holdout.check_holdout(holdout_dir, self.repo_root.name)
        self.assertTrue(report["ok"])
        self.assertEqual(report["collides_with_public_corpus"], [])
        self.assertFalse(report["already_referenced_publicly"])
        self.assertEqual(report["case_count"], 2)

    def test_holdout_identical_to_public_corpus_is_flagged(self):
        with tempfile.TemporaryDirectory() as holdout_dir:
            write_corpus(holdout_dir, make_case("public-1"),
                        make_case("public-2", defect=False))
            report = holdout.check_holdout(holdout_dir, self.repo_root.name)
        self.assertFalse(report["ok"])
        self.assertIn("v2", report["collides_with_public_corpus"])

    def test_fingerprint_already_named_in_experiments_is_flagged(self):
        with tempfile.TemporaryDirectory() as holdout_dir:
            write_corpus(holdout_dir, make_case("private-3"))
            from reviewer.corpus import corpus_fingerprint, load_corpus
            fp = corpus_fingerprint(load_corpus(holdout_dir))
            with open(os.path.join(self.repo_root.name, "eval", "EXPERIMENTS.md"),
                      "a", encoding="utf-8") as fh:
                fh.write(f"| X99 | ... | corpus {fp} | ... |\n")
            report = holdout.check_holdout(holdout_dir, self.repo_root.name)
        self.assertFalse(report["ok"])
        self.assertTrue(report["already_referenced_publicly"])


class MainCliTests(unittest.TestCase):
    def test_refuses_a_cases_path_inside_the_repo(self):
        with tempfile.TemporaryDirectory() as repo:
            os.makedirs(os.path.join(repo, "eval", "cases"))
            inside = os.path.join(repo, "eval", "cases")
            rc = holdout.main(["check", "--cases", inside, "--repo-root", repo])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
