"""Non-Claude authorship pilot tests (M4-B). The invariant under test:
a malformed or schema-invalid model attempt is recorded as REJECTED,
never silently repaired and relabeled as if the model got it right."""

import json
import shutil
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
    "file_path": "src/cache.py",
    "before": ["def cache_key(tenant_id, user_id):",
               "    return f'{tenant_id}:{user_id}'"],
    "after": ["def cache_key(tenant_id, user_id):",
              "    return f'{user_id}'"],
    "defect": True,
    "category": "resource-leak",
    "severity": ["medium", "high"],
    "explanation": "the cache key omits the tenant id, causing cross-tenant reuse",
})

VALID_CLEAN_JSON = json.dumps({
    "title": "add input trimming",
    "language": "python",
    "file_path": "src/util.py",
    "before": ["def norm(s):", "    return s"],
    "after": ["def norm(s):", "    return s.strip()"],
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
            "file_path": "a.py",
            "before": ["x = 1"], "after": ["x = 2"],
            "defect": True, "category": "not-a-real-category",
            "severity": ["medium", "high"], "explanation": "whatever",
        })
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "logic-error", "qwen-pilot-3",
            opener=_FakeOpener(200, {"response": bad}))
        self.assertEqual(record["status"], "rejected-invalid-schema")
        self.assertIsNone(record["proposal"])
        self.assertTrue(any("category" in e for e in record["validation_errors"]))

    def test_language_mismatch_is_rejected_not_relabeled(self):
        # VALID_DEFECT_JSON is a Python case; this attempt asked for Go.
        # The old behaviour stamped the requested language onto the case
        # and returned `ready`, producing a proposal labelled `go` whose
        # diff and affected_files are Python — a wrong label in a scored
        # corpus, and one no human skimming a status column would catch.
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "go", "concurrency", "qwen-pilot-lang",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(record["status"], "rejected-language-mismatch")
        self.assertIsNone(record["proposal"])
        self.assertTrue(any("python" in e.lower()
                            for e in record["validation_errors"]))
        # The raw output is still preserved — a rejected attempt is
        # evidence, not garbage.
        self.assertIn("cache key", record["raw_output"])

    def test_language_echoed_back_unchanged_is_still_ready(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-pilot-lang-ok",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(record["status"], "ready")

    def test_language_omitted_by_the_model_falls_back_to_the_request(self):
        # Nothing to disagree with: the requested language is the only
        # signal there is, and this is the one case where using it is not
        # overriding the model.
        obj = json.loads(VALID_DEFECT_JSON)
        del obj["language"]
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-pilot-lang-none",
            opener=_FakeOpener(200, {"response": json.dumps(obj)}))
        self.assertEqual(record["status"], "ready")
        self.assertEqual(record["proposal"]["case"]["language"], "python")

    def test_language_case_and_whitespace_do_not_cause_a_false_mismatch(self):
        obj = json.loads(VALID_DEFECT_JSON)
        obj["language"] = "  Python  "
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-pilot-lang-ws",
            opener=_FakeOpener(200, {"response": json.dumps(obj)}))
        self.assertEqual(record["status"], "ready")

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


class DeterministicDiffTests(unittest.TestCase):
    """The pilot-2 interface change: the model writes before/after source,
    the harness serializes it into a unified diff. The invariant is that
    serialization can express only what the model wrote."""

    def test_before_after_produce_a_deterministic_unified_diff(self):
        lines = authorpilot.build_unified_diff(
            "a\nb\nc\n", "a\nB\nc\n", "src/x.py")
        again = authorpilot.build_unified_diff(
            "a\nb\nc\n", "a\nB\nc\n", "src/x.py")
        self.assertEqual(lines, again)
        self.assertEqual(lines[0], "--- a/src/x.py")
        self.assertEqual(lines[1], "+++ b/src/x.py")
        self.assertIn("-b", lines)
        self.assertIn("+B", lines)

    def test_generated_diff_contains_no_line_the_model_did_not_write(self):
        before, after = "keep\ndrop\n", "keep\nadd\n"
        lines = authorpilot.build_unified_diff(before, after, "f.py")
        authored = set(before.split()) | set(after.split())
        for line in lines:
            if line.startswith(("---", "+++", "@@")):
                continue
            self.assertIn(line[1:], authored)

    def test_ready_case_diff_is_harness_generated_from_model_source(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-diff",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(record["status"], "ready")
        diff = record["proposal"]["case"]["diff"]
        self.assertEqual(diff[0], "--- a/src/cache.py")
        self.assertIn("-    return f'{tenant_id}:{user_id}'", diff)
        self.assertIn("+    return f'{user_id}'", diff)
        # affected_files restates the model's own file_path, nothing more.
        self.assertEqual(record["proposal"]["case"]["affected_files"],
                         ["src/cache.py"])

    def test_record_states_which_fields_the_harness_generated(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-fields",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertIn("diff", record["harness_generated_fields"])
        self.assertIn("affected_files", record["harness_generated_fields"])
        for substantive in ("before", "after", "category", "severity",
                            "explanation", "defect"):
            self.assertIn(substantive, record["model_authored_fields"])
            self.assertNotIn(substantive, record["harness_generated_fields"])

    def test_harness_does_not_rewrite_model_source(self):
        # Every code line in the generated diff must appear verbatim in
        # the model's raw output. Nothing is reformatted or repaired.
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-verbatim",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        raw = json.loads(record["raw_output"])
        authored = set(raw["before"]) | set(raw["after"])
        for line in record["proposal"]["case"]["diff"]:
            if line.startswith(("---", "+++", "@@")):
                continue
            self.assertIn(line[1:], authored)

    def test_raw_response_preserved_byte_for_byte(self):
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-raw",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(record["raw_output"], VALID_DEFECT_JSON)

    def test_provenance_records_author_model_and_family(self):
        record = authorpilot.run_pilot(
            "deepseek-r1:14b", "deepseek", "python", "concurrency", "ds-prov",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        prov = record["proposal"]["case"]["provenance"]
        self.assertEqual(prov["author_family"], "deepseek")
        self.assertEqual(prov["author_model"], "deepseek-r1:14b")
        # The notes must say the diff was harness-generated — a case that
        # claimed the model wrote the diff would be false.
        self.assertIn("harness", prov["provenance_notes"].lower())


class RejectionTests(unittest.TestCase):
    """Each rejection is its own status, so a reader can tell a no-op from
    a syntax error from a schema violation without reading the message."""

    def _run(self, obj, language="python", case_id="x"):
        return authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", language, "logic-error", case_id,
            opener=_FakeOpener(200, {"response": json.dumps(obj)}))

    def test_noop_before_after_is_rejected(self):
        obj = json.loads(VALID_DEFECT_JSON)
        obj["after"] = list(obj["before"])
        record = self._run(obj, case_id="noop")
        self.assertEqual(record["status"], "rejected-noop")
        self.assertIsNone(record["proposal"])

    def test_invalid_python_source_is_rejected_not_repaired(self):
        obj = json.loads(VALID_DEFECT_JSON)
        # The exact first-pilot failure: edit a line, leave the body's
        # indentation behind.
        obj["after"] = ["def cache_key(tenant_id, user_id):",
                        "    key = user_id",
                        "        return key"]
        record = self._run(obj, case_id="pysyntax")
        self.assertEqual(record["status"], "rejected-syntax")
        self.assertIsNone(record["proposal"])
        self.assertTrue(any("indent" in e.lower()
                            for e in record["validation_errors"]))
        # Raw output survives rejection — evidence, not garbage.
        self.assertIn("return key", record["raw_output"])

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_invalid_javascript_source_is_rejected(self):
        obj = {
            "title": "unclosed function", "language": "javascript",
            "file_path": "src/a.js",
            "before": ["function f(x) {", "  return x;", "}"],
            "after": ["function f(x) {", "  return x;"],
            "defect": True, "category": "logic-error",
            "severity": ["low", "medium"], "explanation": "broken",
        }
        record = self._run(obj, language="javascript", case_id="jssyntax")
        self.assertEqual(record["status"], "rejected-syntax")
        self.assertIsNone(record["proposal"])

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_valid_javascript_source_is_accepted(self):
        obj = {
            "title": "off by one", "language": "javascript",
            "file_path": "src/a.js",
            "before": ["function last(xs) {", "  return xs[xs.length - 1];", "}"],
            "after": ["function last(xs) {", "  return xs[xs.length];", "}"],
            "defect": True, "category": "logic-error",
            "severity": ["medium", "high"],
            "explanation": "reads one past the end of the array",
        }
        record = self._run(obj, language="javascript", case_id="jsok")
        self.assertEqual(record["status"], "ready")

    def test_missing_before_after_is_malformed_not_syntax(self):
        obj = json.loads(VALID_DEFECT_JSON)
        del obj["before"]
        record = self._run(obj, case_id="nobefore")
        self.assertEqual(record["status"], "rejected-malformed")

    def test_missing_file_path_is_malformed(self):
        obj = json.loads(VALID_DEFECT_JSON)
        del obj["file_path"]
        record = self._run(obj, case_id="nopath")
        self.assertEqual(record["status"], "rejected-malformed")

    def test_source_accepted_as_a_plain_string_too(self):
        obj = json.loads(VALID_DEFECT_JSON)
        obj["before"] = "x = 1\n"
        obj["after"] = "x = 2\n"
        record = self._run(obj, case_id="strsrc")
        self.assertEqual(record["status"], "ready")

    def test_a_rejected_attempt_yields_no_proposal_to_repair(self):
        # The structural guarantee behind "Claude cannot silently repair a
        # rejected attempt": a rejection carries proposal=None, so there
        # is no object downstream code could touch up and pass along.
        for mutate, expected in (
            (lambda o: o.update(after=list(o["before"])), "rejected-noop"),
            (lambda o: o.update(after=["  bad indent"]), "rejected-syntax"),
            (lambda o: o.update(category="not-a-real-category"),
             "rejected-invalid-schema"),
        ):
            obj = json.loads(VALID_DEFECT_JSON)
            mutate(obj)
            record = self._run(obj, case_id="norepair")
            self.assertEqual(record["status"], expected)
            self.assertIsNone(record["proposal"])
            self.assertFalse(record["claude_touched"])


class ProposalSeparationTests(unittest.TestCase):
    def test_ready_attempt_stops_at_proposal_and_names_no_corpus(self):
        # A ready attempt produces a *proposal*, status "proposed", and
        # nothing that points at a scored corpus. Admission into
        # eval/cases* is a human step, not something a record can assert.
        record = authorpilot.run_pilot(
            "qwen3.6:27b", "qwen", "python", "resource-leak", "qwen-sep",
            opener=_FakeOpener(200, {"response": VALID_DEFECT_JSON}))
        self.assertEqual(record["proposal"]["status"], "proposed")
        self.assertEqual(record["proposal"]["case"]["status"], "pilot")
        self.assertNotIn("eval/cases", json.dumps(record["proposal"]))


if __name__ == "__main__":
    unittest.main()
