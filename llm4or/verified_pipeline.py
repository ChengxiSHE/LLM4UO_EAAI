"""Post-S1 protocol. Offline validated; requires new approval before live use."""
from copy import deepcopy

from .contracts import LP_SCHEMA, TEACHER_SCHEMA, validate
from .pipeline import PROMPTS, quote_spans, run_problem
from .schema import digest, validate_public
from .solver import execute
from .teacher_facts import compile_teacher_record

VERSION = "lp-pilot-v3-verified-facts"
INITIAL_INSTRUCTION = (
    "Formulate the optimization problem as lp-v1 JSON. This implementation supports continuous linear models only. "
    "Do not treat the word 'LP' as permission to relax counts, discrete activation, fixed charges, or integer decisions. "
    "Unsupported or ambiguous domains must be recorded as failures rather than silently relaxed."
)
MODEL_INSTRUCTION = (
    " Return ONE JSON object with EXACTLY these four top-level keys: schema, variables, constraints, objective. "
    "The schema field is the literal lp-v1. All four fields belong at the root. "
    "Never output request fields such as response_schema, context, problem, output_contract, rules, or version. "
    "The supplied response_schema describes your OUTPUT ONLY; do not copy that schema itself. "
    "Every coefficient object must explicitly include every variable ID, including zeros. "
    "Do not silently relax discrete variables or unsupported mathematics; malformed/unsupported models are recorded as failures."
)
TEACHER_INSTRUCTION = (
    "Return ONE teacher-v2 JSON object matching response_schema. Copy model_hashes and one exact quote/start/end from quote_spans. "
    "Put hypotheses about the problem text in interpretation, which is NOT treated as a verified fact. "
    "Put factual statements about candidate models in typed claims; maximum 8, unique IDs. "
    "declared_bound describes only explicit variable metadata, not whether constraints imply a bound. "
    "Use entails to ask whether ALL feasible points satisfy a specified inequality, including variable bounds. "
    "Use row_coefficient/row_rhs/row_sense to reference exact stored rows by ID, never by array order. "
    "Return repair only with a witnessed target row, at least one teacher-feasible positive example, and a pair of entails claims "
    "on that same row's clause: one initial and one teacher, with opposite expected booleans. "
    "If no executable difference is found, use no_witness with empty target_rows and positive_examples; this is not a proof of correctness. "
    "Use unresolved for unsupported comparison or ambiguity. Do not invent disagreements. No gold answer is available."
)


def make_verified_payload(problem, phase, **context):
    problem = validate_public(problem)
    if phase == "teacher_feedback":
        instruction, contract = TEACHER_INSTRUCTION, TEACHER_SCHEMA
        context["quote_spans"] = quote_spans(problem["text"])
        context["model_hashes"] = {k: digest(context[k]) for k in ("initial", "teacher")}
    else:
        instruction = (INITIAL_INSTRUCTION if phase == "initial" else PROMPTS[phase]) + MODEL_INSTRUCTION
        contract = LP_SCHEMA
    return {"instruction": instruction, "version": VERSION, "problem": problem,
            "context": context, "response_schema": deepcopy(contract)}


def run_verified_problem(problem, gateway, replies, solver=execute):
    return run_problem(problem, gateway, replies, solver,
                       payload_builder=make_verified_payload, prompt_version=VERSION,
                       output_validator=lambda value, phase: validate(value, TEACHER_SCHEMA if phase == "teacher_feedback" else LP_SCHEMA),
                       teacher_validator=lambda raw, p, initial, teacher, evidence:
                           compile_teacher_record(raw, p, initial, teacher, evidence, solver))
