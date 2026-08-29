import argparse
import hashlib
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_rc_observation as observation


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.acceptance = self.directory / "acceptance.json"
        self.load = self.directory / "load.json"
        self.acceptance.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "console_errors": [],
                    "failed_requests": [],
                }
            )
            + "\n"
        )
        self.load.write_text(
            json.dumps({"status": "passed", "failures": []}) + "\n"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def args(self, **overrides):
        values = {
            "acceptance_result": self.acceptance,
            "load_result": self.load,
            "output": self.directory / "observation.json",
            "observed_at": "2026-08-29T02:00:00Z",
            "commit_sha": "a" * 40,
            "evidence_url": (
                "https://github.com/pytincture/pytincture_example/actions/runs/10"
            ),
            "run_id": "10",
            "run_attempt": "2",
            "event": "push",
            "ref": "refs/heads/main",
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    @patch.object(observation, "_version")
    def test_builds_passing_integrity_checked_observation(self, version):
        version.side_effect = {
            "pytincture_example": "0.1.2",
            "pytincture": "1.0.0rc1",
            "dhxpyt": "0.9.16",
        }.__getitem__

        result = observation.build_observation(self.args(), {})

        self.assertEqual(observation.validate_observation(result), [])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["candidate"], "1.0.0rc1")
        self.assertEqual(result["widgetset"], "dhxpyt==0.9.16")
        self.assertEqual(
            result["result_sha256"]["browser_acceptance"],
            hashlib.sha256(self.acceptance.read_bytes()).hexdigest(),
        )

    @patch.object(observation, "_version")
    def test_failed_result_becomes_an_explicit_finding(self, version):
        version.return_value = "1.0.0rc1"
        self.acceptance.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "console_errors": ["boom"],
                    "failed_requests": ["http://example.invalid"],
                }
            )
            + "\n"
        )

        result = observation.build_observation(self.args(), {})

        self.assertEqual(result["status"], "failed")
        self.assertIn("browser acceptance did not pass", result["findings"])
        self.assertIn("browser console errors were observed", result["findings"])
        self.assertIn("browser request failures were observed", result["findings"])

    def test_schema_matches_the_producer(self):
        schema = json.loads(
            (ROOT / "contracts" / "rc-observation-v1.schema.json").read_text()
        )
        self.assertEqual(schema["$id"], observation.SCHEMA_ID)

    def test_workflow_builds_and_retains_the_observation(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("scripts/build_rc_observation.py", workflow)
        self.assertIn("rc1-observation.json", workflow)
        self.assertIn("pytincture-rc1-observation", workflow)


if __name__ == "__main__":
    unittest.main()
