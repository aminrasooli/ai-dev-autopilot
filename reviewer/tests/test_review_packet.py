"""Ground-truth review-packet rendering tests. Offline.

Kept out of test_corpus.py so the `--review` feature and the published
evidence guards stay independently landable — they touch no common file.
"""

import unittest

from reviewer import corpus
from reviewer.tests.test_corpus import make_case


class ReviewPacketTests(unittest.TestCase):
    """`--review` renders ground truth for a human reviewer. It must
    render *everything* a reviewer needs and claim *nothing* about
    whether a review happened."""

    def test_packet_renders_defective_and_clean_sections(self):
        cases = [make_case("d1"), make_case("c1", defect=False)]
        text = corpus.render_review_packet(cases, "somewhere")
        self.assertIn("Defective cases (1)", text)
        self.assertIn("Clean controls (1)", text)
        self.assertIn("`d1`", text)
        self.assertIn("`c1`", text)

    def test_packet_includes_the_answer_key_a_reviewer_must_judge(self):
        case = make_case("d1")
        case["ground_truth"]["accepted_categories"] = ["unsafe-default"]
        text = corpus.render_review_packet([case], "somewhere")
        self.assertIn("logic-error", text)       # primary category
        self.assertIn("unsafe-default", text)    # accepted alternative
        self.assertIn("medium", text)            # severity range
        self.assertIn("why", text)               # explanation
        self.assertIn("-old_d1", text)           # the diff itself

    def test_packet_asserts_no_review_and_warns_about_holdouts(self):
        # A generated file must never read as evidence that a human
        # reviewed anything — that is the exact claim M5's launch gate
        # turns on — and dumping a holdout's answer key is a §11 leak.
        text = corpus.render_review_packet([make_case("d1")], "somewhere")
        self.assertIn("not a review", text)
        self.assertIn("Generating this file establishes nothing", text)
        self.assertIn("Do not commit this file for a private holdout", text)

    def test_packet_does_not_render_a_verdict_field(self):
        text = corpus.render_review_packet([make_case("d1")], "x").lower()
        for leading in ("verdict", "approved", "sign-off", "reviewed by"):
            self.assertNotIn(leading, text)

    def test_clean_case_packet_omits_defect_only_fields(self):
        text = corpus.render_review_packet([make_case("c1", defect=False)], "x")
        self.assertNotIn("**category**", text)
        self.assertNotIn("**severity**", text)
