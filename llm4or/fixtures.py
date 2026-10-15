"""Hand-authored fixtures. These are NOT LLM-generated results or benchmark data."""
from copy import deepcopy

from .gateway import MockReply
from .schema import canonical, digest


def box():
    return {"schema": "lp-v1", "variables": [
        {"id": v, "meaning": v + " production", "unit": "tonne", "domain": "continuous", "lower": 0, "upper": 1}
        for v in ("x", "y")], "constraints": [],
        "objective": {"coefficients": {"x": 1, "y": 0}, "sense": "max", "unit": "profit", "offset": 0}}


def triangle():
    m = box()
    m["constraints"] = [{"id": "capacity", "coefficients": {"x": 1, "y": 1}, "sense": "le", "rhs": 1}]
    return m


def scenario(name="correction"):
    problem = {"id": name, "text": "x and y are continuous production quantities in tonnes, each between zero and one. Total production must not exceed one tonne. Maximize profit equal to x."}
    quote = "Total production must not exceed one tonne."
    packet = {"status": "repair", "quote": quote, "start": problem["text"].index(quote),
              "end": problem["text"].index(quote) + len(quote),
              "explanation": "The initial model permits x=y=1, violating the stated shared capacity.",
              "target_rows": ["capacity"], "positive_examples": [{"x": 0, "y": 1}]}
    proposal = triangle()
    if name == "overconstraint":
        proposal["constraints"][0]["rhs"] = 0
    elif name == "unresolved":
        packet["status"] = "unresolved"
        packet["target_rows"] = []
    replies = {phase: MockReply(canonical(obj), prompt_tokens=100, completion_tokens=100)
               for phase, obj in {"initial": box(), "baseline_repair": box(), "teacher_model": triangle(),
                                  "teacher_feedback": packet, "semantic_repair": proposal}.items()}
    if name == "malformed":
        replies["initial"] = MockReply("```python\nprint('not allowed')\n```")
    return deepcopy(problem), replies, triangle()


def verified_record(initial=None, teacher=None, status="repair"):
    """Hand-authored v3 protocol fixture, never an observed teacher response."""
    import json
    initial, teacher = initial or box(), teacher or triangle()
    _, replies, _ = scenario()
    old = json.loads(replies['teacher_feedback'].text)
    clause = {'coefficients': {'x': 1, 'y': 1}, 'sense': 'le', 'rhs': 1}
    return {'schema': 'teacher-v2', 'status': status,
            'model_hashes': {'initial': digest(initial), 'teacher': digest(teacher)},
            **{k: old[k] for k in ('quote', 'start', 'end')},
            'interpretation': 'The quoted text supports a total capacity of one tonne.',
            'claims': [{'id': 'student_capacity', 'model': 'initial', 'kind': 'entails', **clause, 'expected': False},
                       {'id': 'teacher_capacity', 'model': 'teacher', 'kind': 'entails', **clause, 'expected': True}] if status == 'repair' else [],
            'target_rows': ['capacity'] if status == 'repair' else [],
            'positive_examples': [{'x': 0, 'y': 1}] if status == 'repair' else []}
