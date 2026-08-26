"""Non-Claude authorship pilot tests (M4-B). The invariant under test:
a malformed or schema-invalid model attempt is recorded as REJECTED,
never silently repaired and relabeled as if the model got it right."""

import json
import unittest

from reviewer import authorpilot
from reviewer.errors import MalformedResponse, ReviewerUnavailable


class _FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeOpener:
    def __init__(self, status, body_obj):
        self.status = status
        self.body = json.dumps(body_obj).encode("utf-8")

    def open(self, request, timeout=None):
        return _FakeResponse(self.status, self.body)


class _RaisingOpener:
    def __init__(self, exc):
        self.exc = exc

    def open(self, request, timeout=None):
        raise self.exc


VALID_DEFECT_JSON = json.dumps({
    "title": "cache key missing tenant id",
    "language": "python",
    "affected_files": ["src/cache.py"],
    "diff": ["--- a/src/cache.py", "+++ b/src/cache.py",
            "@@ -1,2 +1,2 @@", "-key = user_id", "+key = f'{user_id}'"],
    "defect": True,
    "category": "resource-leak",
    "severity": ["medium", "high"],
    "explanation": "the cache key omits the tenant id, causing cross-tenant reuse",
})

VALID_CLEAN_JSON = json.dumps({
    "title": "add input trimming",
    "language": "python",
    "affected_files": ["src/util.py"],
    "diff": ["--- a/src/util.py", "+++ b/src/util.py",
            "@@ -1,2 +1,2 @@", "-return s", "+return s.strip()"],
    "defect": False,
    "explanation": "harmless whitespace trimming, no behavior change of concern",
})


class BuildPromptTests(unittest.TestCase):
    def test_rejects_unknown_language(self):
        from reviewer.result import CATEGORIES
        with self.assertRaises(ValueError):
            authorpilot.build_authoring_prompt("cobol", "logic-error", CATEGORIES)

    def test_prompt_names_the_language_and_category(self):
        from reviewer.result import CATEGORIES
        prompt = authorpilot.build_authoring_prompt(
            "python", "resource-leak", CATEGORIES)
        self.assertIn("python", prompt)
        self.assertIn("resource-leak", prompt)


class ParsePilotOutputTests(unittest.TestCase):
    def test_bare_json_parses(self):
        obj = authorpilot.parse_pilot_output(VALID_DEFECT_JSON)
        self.assertTrue(obj["defect"])

    def test_json_embedded_in_prose_is_extracted(self):
        text = f"Sure, here is a case:\n{VALID_CLEAN_JSON}\nHope that helps!"
        obj = authorpilot.parse_pilot_output(text)
        self.assertFalse(obj["defect"])

    def test_no_json_object_raises(self):
        with self.assertRaises(ValueError):
            authorpilot.parse_pilot_output("I refuse to produce JSON today.")


class CallModelTests(unittest.TestCase):
    def test_unreachable_daemon_raises_reviewerunavailable(self):
        with self.assertRaises(ReviewerUnavailable):
            authorpilot.call_model(
                "qwen3.6:27b", "prompt",
                opener=_RaisingOpener(OSError("connection refused")))

    def test_empty_response_field_is_malformed(self):
        with self.assertRaises(MalformedResponse):
            authorpilot.call_model(
                "qwen3.6:27b", "prompt",
                opener=_FakeOpener(200, {"response": ""}))

    def test_happy_path_returns_response_text(self):
        text = authorpilot.call_model(
            "qwen3.6:27b", "prompt",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(text, VALID_DEFECT_JSON)


class RunPilotTests(unittest.TestCase):
    def test_valid_defect_output_produces_ready_proposal(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-pilot-1",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}), now=lambda: 1000.0)
        self.assertEqual(record["status"], "ready")
        self.assertEqual(record["validation_errors"], [])
        self.assertIsNotNone(record["proposal"])
        self.assertEqual(record["proposal"]["author_family"], "qwen")
        self.assertEqual(record["proposal"]["generator"], "qwen3.6:27b")
        self.assertEqual(
            record["proposal"]["case"]["provenance"]["author_model"],
            "qwen3.6:27b")
        self.assertFalse(record["claude_touched"])
        self.assertEqual(record["generated_at"], 1000.0)

    def test_valid_clean_output_produces_ready_proposal(self):
        record = authorpilot.run_pilot(
            "deepseek-r1:14b", "deepseek", "python", "logic-error", "ds-pilot-1",
            opener=_FakeOpener(200, {"response": VALID_CLEAN_JSON}))
        self.assertEqual(record["status"], "ready")
        self.assertFalse(record["proposal"]["case"]["ground_truth"]["defect"])

    def test_malformed_output_is_rejected_not_repaired(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "logic-error", "qwen-pilot-2",
            opener=_FakeOpener(200, {"response": "not json at all, sorry"}))
        self.assertEqual(record["status"], "rejected-malformed")
        self.assertIsNone(record["proposal"])
        self.assertTrue(record["validation_errors"])

    def test_schema_invalid_output_is_rejected_not_repaired(self):
        bad = json.dumps({
            "title": "bad category case", "language": "python",
            "affected_files": ["a.py"],
            "diff": ["--- a/a.py", "+++ b/a.py", "@@ -1 +1 @@", "-x", "+y"],
            "defect": True, "category": "not-a-real-category",
            "severity": ["medium", "high"], "explanation": "whatever",
        })
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "logic-error", "qwen-pilot-3",
            opener=_FakeOpener(200, {"response": bad}))
        self.assertEqual(record["status"], "rejected-invalid-schema")
        self.assertIsNone(record["proposal"])
        self.assertTrue(any("category" in e for e in record["validation_errors"]))

    def test_daemon_unreachable_propagates_not_recorded_as_rejected(self):
        # Infrastructure failure (can't reach the model at all) is
        # distinct from a pilot outcome (model replied, output was bad) —
        # the caller (CLI) decides what to do with it, it is not folded
        # into "rejected".
        with self.assertRaises(ReviewerUnavailable):
            authorpilot.run_pilot(
                "qwen3.6:27b", "qwen", "python", "logic-error", "qwen-pilot-4",
                opener=_RaisingOpener(OSError("connection refused")))

    def test_bad_author_family_rejected_before_any_call(self):
        with self.assertRaises(ValueError):
            authorpilot.run_pilot(
                "some-model", "not-a-real-family", "python", "logic-error",
                "x", opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))


if __name__ == "__main__":
    unittest.main()
