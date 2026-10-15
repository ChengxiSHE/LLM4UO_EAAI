"""Hash-bound, non-executing adapter for the official Chain-of-Experts source.

The upstream repository has no license file and is treated as untrusted input.
Production code therefore reads the pinned Git objects as data, accepts only
literal class constants and constructor metadata, and reimplements the small
forward-only orchestration surface.  It never imports an upstream module.

Two snapshots are intentionally distinct.  ``paper`` preserves the April 2024
controller behavior, including its duplicate expert name and conductor bugs.
``current`` preserves the maintainers' later fixes.  Results from the two must
never be pooled.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import re
import subprocess
from typing import Any


PAPER_COMMIT = "9d96bcc2f067177eb0e122b1aae8227748dc6830"
CURRENT_COMMIT = "afb89bf602690ea621f13a23c42722f20f653a43"

EXPERT_FILES = (
    "experts/terminology_interpreter.py",
    "experts/parameter_extractor.py",
    "experts/modeling_expert.py",
    "experts/programming_example_provider.py",
    "experts/programming_expert.py",
    "experts/modeling_knowledge_supplement_expert.py",
    "experts/code_reviewer.py",
)

# The complete audited surface used by the adapter.  Hashes bind both prompt
# text and controller behavior; they are not fetched at runtime.
SOURCE_HASHES = {
    "paper": {
        "main.py": "126a1c0da1d257ae4dd37d72f1277ac0b32fa7495e70ae8135b754129e3d4f84",
        "conductor.py": "163a3d17ccd0f2093efb10471c5d949c4c94dd59e23685d5af9e01918c95e33a",
        "reducer.py": "6be7399328754c6e2ec9c94ef4e399c7b1c98985444d15ee9421edf00ebdf429",
        "comment_pool.py": "a8c27b96d8c1e51b517678cf17a46c416789de31e386bda7ae6d281309797d0c",
        "comment.py": "872e25ce57f33c6312443567aeb73cbcec7d68662b131a8b7fbb7c8523a9845e",
        "utils.py": "92b1ed52b5560ad88182d0d3732f2ff533867991175aafd8f80f9322e2057ca1",
        "experts/base_expert.py": "abdd87b02fa6c7d6dbd3b6b987d97bb3caa0815b6f315b7b1a5d68831c678b00",
        "experts/terminology_interpreter.py": "91b9dfea1304a9a0ca249b0ca44c66974fa341fb971775a82f2f4998488fdeaa",
        "experts/parameter_extractor.py": "c5f8e8593efb61ac3b62a5ed887863c3f7c498d77367841f07a68fdfbe902157",
        "experts/modeling_expert.py": "82d70bd97992fe314965f723a006f9bbeaf1cb9eab72f9edb3d440f1ad99d40f",
        "experts/programming_example_provider.py": "0b222a7c7f6539907586883af8099af9ca4ea8ed1ff68d6082a0e1b54b4d1fe0",
        "experts/programming_expert.py": "d9721fda1ecaaa9671070449102a8f0a1a785de01c726f3f15365576b717e79d",
        "experts/modeling_knowledge_supplement_expert.py": "d7faafadbc45f11ef971919d07551303b15835835d76e3f0f6264973fdedc338",
        "experts/code_reviewer.py": "2d5c01acc0cb15479287fdfa0b8b116406a603397db9d11f641599b274097105",
    },
    "current": {
        "main.py": "0f2b457f6848013521f6bd9ebf2c2b96045e4b705b43e3ca1290493710bfc1c8",
        "conductor.py": "024494087cb8524ba254c9226a1112f755d5b37d128d7a5ee2dbde205fcf4a64",
        "reducer.py": "65a196cfc52739b194a184a3d4ec23c94566c739272f6d8ed60a0b3b54c963bf",
        "comment_pool.py": "91420b34acfc8f638a5268ff87f777419a5d4143aebf8a1fb20d679d45293065",
        "comment.py": "872e25ce57f33c6312443567aeb73cbcec7d68662b131a8b7fbb7c8523a9845e",
        "utils.py": "62f70638599b4a65913406f848da696793a052900289f6cb0e9a6acb77dd2e81",
        "experts/base_expert.py": "52d9f65a3971fd9fa939f51e4ec6f73c0c70c8dd00e042ed1cdd1c5346753800",
        "experts/terminology_interpreter.py": "be84cbe7a05c1659c98e81d5773b54ff0ac26c0af11d64b6b20b47d4cab05cff",
        "experts/parameter_extractor.py": "ab4cbf80dc6e788004d3d371874b175bdec4fa5ad5b94a3fc79416805d9a9a23",
        "experts/modeling_expert.py": "e473f2af322782bd4662c9cce4e83cd72ab7e9c3812c603d964f304affec26c4",
        "experts/programming_example_provider.py": "fcfcc5c61ece4a78025c2b23164d77a647287fb23b39031bd867b2ffbcd0eca8",
        "experts/programming_expert.py": "5d3c8b58f14b08b85ac256de3d73aec5a2520f313ccd02ddb4eb0584001b7e7c",
        "experts/modeling_knowledge_supplement_expert.py": "c54b6fbc33f44e1b4af0475268793df49d1bff576a3c79011d5f99d0f907a485",
        "experts/code_reviewer.py": "5f63a525e18077acf07be0b84325e46f2fc7b552098e40697d77c5f45ade41ba",
    },
}


class CoESourceError(RuntimeError):
    """Pinned source is missing, changed, or outside the literal contract."""


@dataclass(frozen=True)
class ExpertSpec:
    key: str
    class_name: str
    name: str
    description: str
    role_description: str
    forward_task: str

    @property
    def prompt_template(self) -> str:
        return self.role_description + "\n" + self.forward_task

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"


@dataclass(frozen=True)
class Comment:
    expert_key: str
    expert_name: str
    text: str | None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_object(root: Path, commit: str, path: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), "show", f"{commit}:{path}"],
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise CoESourceError(f"pinned_coe_source_missing:{path}") from exc


def _literal_class(tree: ast.Module) -> ast.ClassDef:
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1:
        raise CoESourceError("unexpected_upstream_class_count")
    return classes[0]


def _class_string(node: ast.ClassDef, name: str) -> str:
    for item in node.body:
        if isinstance(item, ast.Assign) and len(item.targets) == 1 \
                and isinstance(item.targets[0], ast.Name) and item.targets[0].id == name:
            try:
                value = ast.literal_eval(item.value)
            except (ValueError, TypeError) as exc:
                raise CoESourceError(f"nonliteral_upstream_class_value:{name}") from exc
            if isinstance(value, str):
                return value
    raise CoESourceError(f"missing_upstream_class_value:{name}")


def _constructor_metadata(node: ast.ClassDef) -> tuple[str, str]:
    initializers = [item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == "__init__"]
    if len(initializers) != 1:
        raise CoESourceError("unexpected_upstream_initializer")
    for item in ast.walk(initializers[0]):
        if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Attribute) \
                or item.func.attr != "__init__":
            continue
        values: dict[str, Any] = {}
        for keyword in item.keywords:
            if keyword.arg in {"name", "description"}:
                try:
                    values[keyword.arg] = ast.literal_eval(keyword.value)
                except (ValueError, TypeError) as exc:
                    raise CoESourceError("nonliteral_upstream_expert_metadata") from exc
        if set(values) == {"name", "description"} and all(isinstance(v, str) for v in values.values()):
            return values["name"], values["description"]
    raise CoESourceError("missing_upstream_expert_metadata")


def _first_json_blob(text: str) -> str | None:
    for start, character in enumerate(text):
        if character not in "[{":
            continue
        stack: list[str] = []
        quote = None
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if quote is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in "\"'":
                quote = char
            elif char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack or (stack.pop(), char) not in {("[", "]"), ("{", "}")}:
                    break
                if not stack:
                    return text[start:index + 1]
    return None


def _current_json(text: str) -> Any:
    raw = str(text).strip()
    blocks = re.findall(r"```(?:python)?\s*(.*?)\s*```", raw, re.DOTALL)
    code = raw if not blocks else blocks[0] if len(blocks) == 1 else "\n".join(
        block for block in blocks if "pip" not in block
    )
    candidates = [value for value in (raw, code.strip(), _first_json_blob(raw), _first_json_blob(code)) if value]
    for candidate in dict.fromkeys(candidates):
        for parser in (json.loads, ast.literal_eval):
            try:
                return parser(candidate)
            except (ValueError, SyntaxError, json.JSONDecodeError):
                pass
    raise ValueError("cannot_parse_coe_json")


@dataclass(frozen=True)
class CoEPromptSource:
    root: Path
    snapshot: str
    commit: str
    experts: tuple[ExpertSpec, ...]
    conductor_role: str
    conductor_task: str
    reducer_role: str
    reducer_task: str

    @classmethod
    def load(cls, repository: str | Path, snapshot: str) -> "CoEPromptSource":
        if snapshot not in {"paper", "current"}:
            raise CoESourceError("unknown_coe_snapshot")
        root = Path(repository).resolve()
        if not (root / ".git").is_dir():
            raise CoESourceError("pinned_coe_repository_missing")
        commit = PAPER_COMMIT if snapshot == "paper" else CURRENT_COMMIT
        sources: dict[str, str] = {}
        for path, expected in SOURCE_HASHES[snapshot].items():
            data = _git_object(root, commit, path)
            if _sha(data) != expected:
                raise CoESourceError(f"pinned_coe_source_changed:{path}")
            sources[path] = data.decode("utf-8")

        experts = []
        for path in EXPERT_FILES:
            node = _literal_class(ast.parse(sources[path]))
            name, description = _constructor_metadata(node)
            experts.append(ExpertSpec(
                key=Path(path).stem,
                class_name=node.name,
                name=name,
                description=description,
                role_description=_class_string(node, "ROLE_DESCRIPTION"),
                forward_task=_class_string(node, "FORWARD_TASK"),
            ))
        conductor = _literal_class(ast.parse(sources["conductor.py"]))
        reducer = _literal_class(ast.parse(sources["reducer.py"]))
        return cls(
            root=root, snapshot=snapshot, commit=commit, experts=tuple(experts),
            conductor_role=_class_string(conductor, "ROLE_DESCRIPTION"),
            conductor_task=_class_string(conductor, "FORWARD_TASK"),
            reducer_role=_class_string(reducer, "ROLE_DESCRIPTION"),
            reducer_task=_class_string(reducer, "FORWARD_TASK"),
        )

    @staticmethod
    def comment_text(comments: list[Comment] | tuple[Comment, ...], *, fixed: bool) -> str:
        if not comments:
            return "There is no comment available, please ignore this section.\n"
        output = ""
        for comment in comments:
            value = ("" if comment.text is None else str(comment.text)) if fixed else comment.text
            if value is None:
                # The paper source raises here.  Preserve that failure instead
                # of silently applying the later fix.
                raise TypeError("paper_comment_none")
            output += comment.expert_name + ": ```" + value + "```\n"
        return output

    def conductor_prompt(self, description: str, comments: list[Comment], maximum: int) -> str:
        if type(maximum) is not int or maximum <= 0:
            raise ValueError("coe_positive_collaboration_budget_required")
        names = [expert.name for expert in self.experts]
        commented = [comment.expert_name for comment in comments]
        if self.snapshot == "paper":
            remaining = list(set(names) - set(commented))
            # Paper bug: len() is applied to the rendered string, not the list.
            remaining_count = maximum - len(str(commented))
        else:
            remaining = [name for name in names if name not in commented]
            remaining_count = max(0, maximum - len(commented))
        values = {
            "problem_description": description,
            "experts_info": "\n".join(str(expert) for expert in self.experts),
            "commented_experts": str(commented),
            "remaining_experts": str(remaining),
            "max_collaborate_nums": maximum,
            "remaining_collaborate_nums": remaining_count,
        }
        return self.conductor_role + "\n" + self.conductor_task.format(**values)

    def choose_expert(self, answer: str, comments: list[Comment], rng: random.Random) -> ExpertSpec:
        if self.snapshot == "current":
            commented = {comment.expert_name for comment in comments}
            remaining = [expert for expert in self.experts if expert.name not in commented]
            for expert in remaining:
                if expert.name in answer:
                    return expert
            # This dict intentionally uses the last duplicate, matching source.
            by_name = {expert.name: expert for expert in self.experts}
            for name, expert in by_name.items():
                if name in answer:
                    return expert
            return rng.choice(remaining or list(by_name.values()))
        by_name = {expert.name: expert for expert in self.experts}
        for name, expert in by_name.items():
            if name in answer:
                return expert
        return rng.choice(list(by_name.values()))

    def expert_prompt(self, expert: ExpertSpec, description: str, code_example: str,
                      comments: list[Comment]) -> str:
        if expert not in self.experts:
            raise ValueError("unknown_coe_expert")
        values = {
            "problem_description": description,
            "code_example": code_example,
            "comments_text": self.comment_text(comments, fixed=self.snapshot == "current"),
            "knowledge": "None",
        }
        return expert.prompt_template.format(**values)

    def process_expert_output(self, expert: ExpertSpec, output: str) -> str:
        if expert.key == "modeling_expert":
            return output.replace(" < ", " \\leq ").replace(" > ", " \\geq ")
        if expert.key != "terminology_interpreter":
            return output
        parsed = json.loads(output) if self.snapshot == "paper" else _current_json(output)
        if self.snapshot == "paper":
            return "".join(item["terminology"] + ":" + item["interpretation"] + "\n" for item in parsed)
        if isinstance(parsed, dict):
            parsed = [parsed]
        answer = ""
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                terminology, interpretation = item.get("terminology"), item.get("interpretation")
                if terminology is None and interpretation is None:
                    continue
                answer += f"{terminology}:{interpretation}\n"
        return answer if answer.strip() else str(output).strip()

    def reducer_prompt(self, description: str, comments: list[Comment]) -> str:
        values = {
            "problem_description": description,
            "comment_text": self.comment_text(comments, fixed=self.snapshot == "current"),
        }
        return self.reducer_role + "\n" + self.reducer_task.format(**values)


__all__ = [
    "CURRENT_COMMIT", "PAPER_COMMIT", "Comment", "CoEPromptSource",
    "CoESourceError", "ExpertSpec", "SOURCE_HASHES",
]
