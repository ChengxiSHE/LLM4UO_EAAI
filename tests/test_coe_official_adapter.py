import random
import unittest
from pathlib import Path

from llm4or.coe_official_adapter import Comment, CoEPromptSource


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "data/raw/xzymustbexzy__Chain-of-Experts_20261003"


@unittest.skipUnless((UPSTREAM / ".git").is_dir(), "ignored upstream CoE checkout unavailable")
class CoEOfficialAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paper = CoEPromptSource.load(UPSTREAM, "paper")
        cls.current = CoEPromptSource.load(UPSTREAM, "current")

    def test_snapshots_preserve_duplicate_name_fix(self):
        paper_names = [expert.name for expert in self.paper.experts]
        current_names = [expert.name for expert in self.current.experts]
        self.assertEqual(paper_names.count("Programming Expert"), 2)
        self.assertEqual(current_names.count("Programming Expert"), 1)
        self.assertIn("Programming Example Provider", current_names)

    def test_empty_comment_text_is_byte_exact(self):
        expected = "There is no comment available, please ignore this section.\n"
        self.assertEqual(self.paper.comment_text([], fixed=False), expected)
        self.assertEqual(self.current.comment_text([], fixed=True), expected)

    def test_current_conductor_excludes_already_selected_expert(self):
        first = self.current.experts[0]
        comments = [Comment(first.key, first.name, "x")]
        prompt = self.current.conductor_prompt("p", comments, 5)
        remaining_line = next(line for line in prompt.splitlines() if line.startswith("Please select"))
        self.assertNotIn(first.name, remaining_line)
        self.assertIn("you can ask 4 more times", prompt)

    def test_paper_conductor_preserves_string_length_bug(self):
        first = self.paper.experts[0]
        comments = [Comment(first.key, first.name, "x")]
        prompt = self.paper.conductor_prompt("p", comments, 5)
        expected = 5 - len(str([first.name]))
        self.assertIn(f"you can ask {expected} more times", prompt)

    def test_paper_duplicate_name_resolves_to_last_expert(self):
        chosen = self.paper.choose_expert("Programming Expert", [], random.Random(0))
        self.assertEqual(chosen.key, "programming_expert")

    def test_current_terminology_parser_accepts_fenced_json(self):
        expert = self.current.experts[0]
        result = self.current.process_expert_output(
            expert, 'preface\n```json\n[{"terminology":"x","interpretation":"y"}]\n```',
        )
        self.assertEqual(result, "x:y\n")

    def test_modeling_postprocess_matches_author_source(self):
        expert = next(item for item in self.current.experts if item.key == "modeling_expert")
        self.assertEqual(
            self.current.process_expert_output(expert, "x < y and z > q"),
            "x \\leq y and z \\geq q",
        )


if __name__ == "__main__":
    unittest.main()
