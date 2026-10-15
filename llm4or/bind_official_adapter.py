"""Hash-bound, non-executing adapter for the official Text2Opt/BIND prompts.

The upstream file is parsed as data.  No third-party Python is imported or
executed.  Only literal prompt constants and the field-annotation dictionary
are accepted, and the prompt-building logic below mirrors the pinned MIT
source at commit 1dac06be656c41d827ef20987cf8af0b48d382a2.
"""

from dataclasses import dataclass
import ast
import hashlib
import math
from pathlib import Path
import textwrap
from typing import Any


UPSTREAM_COMMIT = "1dac06be656c41d827ef20987cf8af0b48d382a2"
UPSTREAM_AGENTIC_SHA256 = "3c6f483b57d155d43a66e9fb754548bb16083c24c8b25c64427fc3ca1a0631a1"
UPSTREAM_RUNNER_SHA256 = "c06ed39ef61e656cf86d14f3b95fd126725a4138c2c525207d5ab9af2613bb42"


class BindSourceError(RuntimeError):
    """The pinned official source is absent, changed, or not purely literal."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _literal_prompt_value(node: ast.AST) -> Any:
    """Evaluate only literals plus ``textwrap.dedent(literal).strip()``."""
    if isinstance(node, (ast.Constant, ast.Dict, ast.List, ast.Tuple, ast.Set)):
        return ast.literal_eval(node)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_prompt_value(node.left)
        right = _literal_prompt_value(node.right)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
    if (
        isinstance(node, ast.Call) and not node.args and not node.keywords
        and isinstance(node.func, ast.Attribute) and node.func.attr == "strip"
    ):
        value = _literal_prompt_value(node.func.value)
        if isinstance(value, str):
            return value.strip()
    if (
        isinstance(node, ast.Call) and len(node.args) == 1 and not node.keywords
        and isinstance(node.func, ast.Attribute) and node.func.attr == "dedent"
        and isinstance(node.func.value, ast.Name) and node.func.value.id == "textwrap"
    ):
        value = _literal_prompt_value(node.args[0])
        if isinstance(value, str):
            return textwrap.dedent(value)
    raise BindSourceError("unsupported_nonliteral_upstream_prompt_definition")


def _literal_assignments(source: str, required: set[str]) -> dict[str, Any]:
    tree = ast.parse(source)
    values: dict[str, Any] = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target, value = statement.targets[0], statement.value
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            target, value = statement.target, statement.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id in required:
            values[target.id] = _literal_prompt_value(value)
    missing = required - set(values)
    if missing:
        raise BindSourceError("missing_upstream_prompt_definitions:" + ",".join(sorted(missing)))
    return values


@dataclass(frozen=True)
class BindPromptSource:
    root: Path
    system_prompt: str
    requirements: str
    template: str
    annotations: dict[str, dict[str, str]]

    @classmethod
    def load(cls, repository: str | Path) -> "BindPromptSource":
        root = Path(repository).resolve()
        prompt_file = root / "main/evaluation/agentic_offload.py"
        runner_file = root / "main/evaluation/run_eval.py"
        if not prompt_file.is_file() or not runner_file.is_file():
            raise BindSourceError("pinned_bind_source_missing")
        if _sha256(prompt_file) != UPSTREAM_AGENTIC_SHA256:
            raise BindSourceError("pinned_bind_agentic_source_changed")
        if _sha256(runner_file) != UPSTREAM_RUNNER_SHA256:
            raise BindSourceError("pinned_bind_runner_source_changed")
        values = _literal_assignments(prompt_file.read_text(), {
            "AGENTIC_SYSTEM_PROMPT", "_INSTANCE_DATA_CODE_REQUIREMENTS",
            "_INSTANCE_DATA_CODE_TEMPLATE", "_FIELD_ANNOTATIONS",
        })
        annotations = values["_FIELD_ANNOTATIONS"]
        if not isinstance(annotations, dict) or any(not isinstance(v, dict) for v in annotations.values()):
            raise BindSourceError("invalid_upstream_field_annotations")
        return cls(
            root=root,
            system_prompt=values["AGENTIC_SYSTEM_PROMPT"],
            requirements=values["_INSTANCE_DATA_CODE_REQUIREMENTS"],
            template=values["_INSTANCE_DATA_CODE_TEMPLATE"],
            annotations=annotations,
        )

    @staticmethod
    def _list_shape(value: Any) -> str:
        if not isinstance(value, list):
            return ""
        if not value:
            return "[0]"
        return f"[{len(value)}]" + BindPromptSource._list_shape(value[0])

    @staticmethod
    def _context(problem_data: dict[str, Any]) -> str:
        template = problem_data.get("LLM_description_template", "").strip()
        if template:
            for key in problem_data.get("instance_data", {}):
                template = template.replace("{" + key.upper() + "}", f'`d["{key}"]`')
            return template
        description = problem_data.get("LLM_description", "").strip()
        if not description:
            return f"Problem type: {problem_data.get('meta', {}).get('problem_type', 'optimization')}"
        cut = len(description)
        for marker in ("Annex", "Appendix", "---\n", "===\n"):
            position = description.find(marker)
            if 0 < position < cut:
                cut = position
        return description[:cut].strip()

    def _schema(self, problem_data: dict[str, Any]) -> str:
        instance_data = problem_data.get("instance_data", {})
        problem_type = problem_data.get("meta", {}).get("problem_type", "")
        annotations = self.annotations.get(problem_type, {})
        lines = []
        for key, value in instance_data.items():
            annotation = annotations.get(key, "")
            if isinstance(value, bool):
                base = f"bool = {value}"
            elif isinstance(value, (int, float)):
                base = f"number = {value}"
            elif isinstance(value, list):
                shape = self._list_shape(value)
                dimensions = shape.replace("][", "×").replace("[", "").replace("]", "")
                base = f"list{shape}  — shape {dimensions}"
            else:
                base = f"value = {value}"
            suffix = f"  [{annotation}]" if annotation else ""
            lines.append(f"  {key:<30s} : {base}{suffix}")
        return "\n".join(lines)

    def initial_prompt(self, problem_data: dict[str, Any], virtual_path: str) -> str:
        """Reproduce upstream ``build_instance_data_prompt`` byte for byte."""
        if not problem_data.get("instance_data"):
            raise BindSourceError("bind_instance_data_required")
        meta = problem_data.get("meta", {})
        problem_type = meta.get("problem_type", "optimization")
        goal = meta.get("goal", "")
        schema = self._schema(problem_data)
        context = self._context(problem_data)
        template = self.template.replace("<FILL_IN_PATH>", virtual_path)
        # Keep the upstream f-string's indentation semantics.  Because inserted
        # context lines can start at column zero, its textwrap.dedent call often
        # leaves eight leading spaces on static lines.
        return f"""Solve the following {problem_type} optimization problem using Gurobi.
        Goal: {goal}

        --- Problem Description ---
        {context}

        --- Numeric Data ---
        All numeric data is stored in a local JSON file — do NOT embed values in code.

        INSTANCE_DATA_PATH = r"{virtual_path}"

        Instance data fields (accessible via json.load, then d["key"]):
        {schema}

        {self.requirements}

        Use this template as your starting point:
        {template}
        """.strip()


@dataclass(frozen=True)
class BindEvaluation:
    execution_succeeded: bool
    status_optimal: bool
    objective_matches: bool
    objective_value: float | None
    reference_optimum: float
    solver_status: int | None
    reference_status: int | None
    num_vars: int | None
    num_constraints: int | None
    reference_num_vars: int | None
    reference_num_constraints: int | None
    stderr: str = ""


def _structural_comparison(evaluation: BindEvaluation) -> str:
    hints = []
    if evaluation.objective_value is not None:
        generated = evaluation.objective_value
        reference = evaluation.reference_optimum
        if reference != 0:
            percent = (generated - reference) / abs(reference) * 100
            direction = "too high" if percent > 0 else "too low"
            hints.append(
                f"  - Your objective value : {generated:.6g}\n"
                f"  - Expected objective   : {reference:.6g} (yours is {abs(percent):.1f}% {direction})"
            )
        else:
            hints.append(
                f"  - Your objective value : {generated:.6g}\n"
                f"  - Expected objective   : {reference:.6g}"
            )
    else:
        hints.append(
            "  - Your objective value : (not available)\n"
            f"  - Expected objective   : {evaluation.reference_optimum:.6g}"
        )
    status_names = {2: "OPTIMAL", 3: "INFEASIBLE", 4: "INF_OR_UNBD", 5: "UNBOUNDED"}
    if evaluation.solver_status != evaluation.reference_status:
        generated_status = status_names.get(evaluation.solver_status, str(evaluation.solver_status))
        reference_status = status_names.get(evaluation.reference_status, str(evaluation.reference_status))
        hints.append(
            f"  - Your solver status   : {generated_status} (code {evaluation.solver_status})\n"
            f"  - Expected status      : {reference_status} (code {evaluation.reference_status})"
        )
    if evaluation.num_vars is not None:
        variable_match = "✓" if evaluation.num_vars == evaluation.reference_num_vars else "MISMATCH"
        constraint_match = "✓" if evaluation.num_constraints == evaluation.reference_num_constraints else "MISMATCH"
        hints.append(
            f"  - Your model structure : {evaluation.num_vars} variables, {evaluation.num_constraints} constraints\n"
            f"  - Expected structure   : {evaluation.reference_num_vars} variables, "
            f"{evaluation.reference_num_constraints} constraints "
            f"[vars: {variable_match}, constrs: {constraint_match}]"
        )
    return "\n".join(hints)


def repair_prompt(evaluation: BindEvaluation, virtual_path: str) -> str:
    """Mirror the official oracle-guided ``build_repair_prompt``."""
    stderr = evaluation.stderr.strip()
    stderr_tail = stderr[-1600:] if stderr else "(empty)"
    path_reminder = (
        f"\n  The data file path has not changed — use exactly this hardcoded path:\n"
        f"  INSTANCE_DATA_PATH = r\"{virtual_path}\"  (or PROBLEM_ARRAY_PATH for array mode)\n"
    )
    structural = _structural_comparison(evaluation)
    return textwrap.dedent(
        f"""
        The previous code did not pass evaluation. Return a complete fixed replacement.

        Evaluation signals:
          - execution_succeeded : {evaluation.execution_succeeded}
          - status_optimal      : {evaluation.status_optimal}
          - objective_matches   : {evaluation.objective_matches}

        Detailed comparison:
        {structural}

        stderr (last 1600 chars):
        {stderr_tail}
        {path_reminder}
        Diagnosis hints:
          - If your objective is wrong but status is OPTIMAL, you likely have a modeling
            error: wrong coefficients, missing/extra terms, or misread problem data.
          - If variable/constraint counts differ, you may be missing decision variables
            or constraints described in the problem.
          - If status is INFEASIBLE, check constraint directions (<=, >=, ==) and bounds.
          - Re-read the original problem description carefully and compare with your code.

        Requirements:
          - Load data from the hardcoded file path at the top of the script.
          - No try/except blocks. No mock implementations.
          - Use correct gurobipy constants: GRB.CONTINUOUS, GRB.INTEGER, GRB.BINARY,
            GRB.MINIMIZE, GRB.MAXIMIZE (NOT GRB_CONTINUOUS, GRB_INTEGER, etc.)
          - Return the Gurobi model object m from solve_problem().
        """
    ).strip()


def objective_match(computed: float | None, reference: float) -> bool:
    return computed is not None and math.isclose(computed, reference, rel_tol=1e-5, abs_tol=1e-6)


__all__ = [
    "BindEvaluation", "BindPromptSource", "BindSourceError", "UPSTREAM_COMMIT",
    "UPSTREAM_AGENTIC_SHA256", "UPSTREAM_RUNNER_SHA256", "objective_match", "repair_prompt",
]
