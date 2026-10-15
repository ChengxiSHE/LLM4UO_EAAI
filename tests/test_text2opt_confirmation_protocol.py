import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Text2OptConfirmationProtocolTests(unittest.TestCase):
    def test_protocol_is_input_only_and_fully_bound(self):
        protocol = json.loads(
            (ROOT / "experiments/text2opt_confirmation_protocol.json").read_text()
        )
        self.assertEqual(protocol["cohorts"]["combined"], {"records": 431, "categories": 7})
        self.assertFalse(protocol["outcomes_read_while_freezing"])
        self.assertEqual(protocol["api_requests"], 0)
        for name, expected in protocol["frozen_files"].items():
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, name)


if __name__ == "__main__":
    unittest.main()
