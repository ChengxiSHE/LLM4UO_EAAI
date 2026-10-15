"""Typed, hash-bound skills for verified harness evolution.

Candidate generators may propose JSON packages accepted by this module.  They
cannot contribute executable Python: every parser/compiler pair must already
exist in an explicitly supplied trusted registry and match its frozen digest.
The public-text recognizer is deliberately small and total.  Ambiguous matches
fail closed so a caller can preserve its backend result exactly.
"""

from copy import deepcopy
import math

from .benchmark_inputs import payload_sha256, validate_public_input
from .schema import canonical, digest


VERSION = "verified-typed-skill-library-v1"
SKILL_SCHEMA = "verified-typed-skill-v1"
SKILL_SCHEMA_V2 = "verified-typed-skill-v2"
EVENT_SCHEMA = "verified-skill-promotion-event-v1"


class InvalidSkill(ValueError):
    pass


def _exact_keys(value, expected, reason):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise InvalidSkill(reason)


def _bounded_text(value, maximum, reason):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise InvalidSkill(reason)
    return value


def _sha256(value, *, nullable=False, reason="invalid_sha256"):
    if value is None and nullable:
        return value
    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise InvalidSkill(reason)
    return value


def _phrases(value, reason):
    if not isinstance(value, list) or len(value) > 32:
        raise InvalidSkill(reason)
    out = []
    for phrase in value:
        text = _bounded_text(phrase, 200, reason).casefold()
        if text != phrase:
            raise InvalidSkill(reason + "_must_be_casefolded")
        out.append(text)
    if len(set(out)) != len(out):
        raise InvalidSkill(reason + "_duplicate")
    return out


def _bounded_json(value, *, depth=0):
    """Validate configuration as inert, bounded JSON data."""
    if depth > 12:
        raise InvalidSkill("configuration_depth")
    if value is None or type(value) in (str, bool, int):
        if isinstance(value, str) and len(value) > 5_000:
            raise InvalidSkill("configuration_string")
        return deepcopy(value)
    if type(value) is float:
        if not math.isfinite(value):
            raise InvalidSkill("configuration_number")
        return value
    if isinstance(value, list):
        if len(value) > 512:
            raise InvalidSkill("configuration_list")
        return [_bounded_json(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 512 or any(not isinstance(key, str) or not key or len(key) > 200
                                   for key in value):
            raise InvalidSkill("configuration_object")
        return {key: _bounded_json(item, depth=depth + 1) for key, item in value.items()}
    raise InvalidSkill("configuration_json_type")


def validate_skill_package(package, trusted_implementations):
    """Validate and detach a declarative skill package.

    ``trusted_implementations`` maps an implementation identifier to its
    precomputed source/artifact digest.  The package may select one of those
    entries but cannot add a new executable implementation.
    """
    if len(canonical(package).encode()) > 100_000:
        raise InvalidSkill("skill_package_too_large")
    _exact_keys(package, {
        "schema", "skill_id", "version", "parent_sha256", "family",
        "recognizer", "implementation", "contracts", "invariants",
        "metamorphic_tests", "limits", "fallback", "provenance",
    }, "invalid_skill_fields")
    if package["schema"] not in {SKILL_SCHEMA, SKILL_SCHEMA_V2}:
        raise InvalidSkill("invalid_skill_schema")
    _bounded_text(package["skill_id"], 80, "invalid_skill_id")
    if not package["skill_id"].replace("_", "").replace("-", "").isalnum():
        raise InvalidSkill("invalid_skill_id")
    if type(package["version"]) is not int or package["version"] < 1:
        raise InvalidSkill("invalid_skill_version")
    _sha256(package["parent_sha256"], nullable=True, reason="invalid_parent_sha256")
    _bounded_text(package["family"], 100, "invalid_family")

    recognizer = package["recognizer"]
    _exact_keys(recognizer, {"kind", "required_all", "required_any", "forbidden_any"},
                "invalid_recognizer_fields")
    if recognizer["kind"] != "casefolded_literal_v1":
        raise InvalidSkill("unsupported_recognizer")
    required_all = _phrases(recognizer["required_all"], "invalid_required_all")
    forbidden_any = _phrases(recognizer["forbidden_any"], "invalid_forbidden_any")
    if not isinstance(recognizer["required_any"], list) or len(recognizer["required_any"]) > 16:
        raise InvalidSkill("invalid_required_any")
    required_any = [_phrases(group, "invalid_required_any_group") for group in recognizer["required_any"]]
    if any(not group for group in required_any) or not required_all and not required_any:
        raise InvalidSkill("empty_positive_recognizer")
    if set(required_all) & set(forbidden_any):
        raise InvalidSkill("contradictory_recognizer")

    implementation = package["implementation"]
    expected_implementation_fields = (
        {"id", "sha256", "configuration"}
        if package["schema"] == SKILL_SCHEMA_V2 else {"id", "sha256"}
    )
    _exact_keys(implementation, expected_implementation_fields, "invalid_implementation_fields")
    implementation_id = _bounded_text(implementation["id"], 120, "invalid_implementation_id")
    implementation_sha256 = _sha256(implementation["sha256"], reason="invalid_implementation_sha256")
    if not isinstance(trusted_implementations, dict):
        raise InvalidSkill("invalid_trusted_registry")
    if trusted_implementations.get(implementation_id) != implementation_sha256:
        raise InvalidSkill("untrusted_or_changed_implementation")
    if package["schema"] == SKILL_SCHEMA_V2:
        configuration = _bounded_json(implementation["configuration"])
        if len(canonical(configuration).encode()) > 50_000:
            raise InvalidSkill("configuration_too_large")

    contracts = package["contracts"]
    _exact_keys(contracts, {"input_schema", "output_schema", "semantic_contract"},
                "invalid_contract_fields")
    if contracts["input_schema"] != "public-problem-v1" or contracts["output_schema"] != "trusted-solve-result-v1":
        raise InvalidSkill("unsupported_skill_contract")
    _bounded_text(contracts["semantic_contract"], 2_000, "invalid_semantic_contract")

    invariants = package["invariants"]
    if not isinstance(invariants, list) or not invariants or len(invariants) > 64:
        raise InvalidSkill("invalid_invariants")
    for invariant in invariants:
        _bounded_text(invariant, 500, "invalid_invariant")

    tests = package["metamorphic_tests"]
    if not isinstance(tests, list) or not tests or len(tests) > 64:
        raise InvalidSkill("invalid_metamorphic_tests")
    test_ids = []
    for test in tests:
        _exact_keys(test, {"id", "transform", "expectation"}, "invalid_metamorphic_test")
        test_ids.append(_bounded_text(test["id"], 80, "invalid_metamorphic_test_id"))
        _bounded_text(test["transform"], 500, "invalid_metamorphic_transform")
        _bounded_text(test["expectation"], 500, "invalid_metamorphic_expectation")
    if len(test_ids) != len(set(test_ids)):
        raise InvalidSkill("duplicate_metamorphic_test_id")

    limits = package["limits"]
    _exact_keys(limits, {"max_input_bytes", "max_variables", "max_constraints", "wall_seconds"},
                "invalid_limit_fields")
    ceilings = {"max_input_bytes": 1_000_000, "max_variables": 20_000,
                "max_constraints": 50_000, "wall_seconds": 300}
    for key, ceiling in ceilings.items():
        if type(limits[key]) is not int or not 1 <= limits[key] <= ceiling:
            raise InvalidSkill("invalid_" + key)
    if package["fallback"] != "unchanged_backend":
        raise InvalidSkill("unsafe_fallback")

    provenance = package["provenance"]
    _exact_keys(provenance, {"proposer", "development_manifest_sha256", "proposal_sha256"},
                "invalid_provenance_fields")
    _bounded_text(provenance["proposer"], 120, "invalid_proposer")
    _sha256(provenance["development_manifest_sha256"], reason="invalid_development_manifest_sha256")
    _sha256(provenance["proposal_sha256"], reason="invalid_proposal_sha256")
    return deepcopy(package)


def skill_sha256(package, trusted_implementations):
    return digest(validate_skill_package(package, trusted_implementations))


def recognizer_matches(package, public_text, trusted_implementations):
    skill = validate_skill_package(package, trusted_implementations)
    if not isinstance(public_text, str):
        raise InvalidSkill("invalid_public_text")
    if len(public_text.encode()) > skill["limits"]["max_input_bytes"]:
        return False
    text = public_text.casefold()
    rule = skill["recognizer"]
    return (
        all(phrase in text for phrase in rule["required_all"])
        and all(any(phrase in text for phrase in group) for group in rule["required_any"])
        and not any(phrase in text for phrase in rule["forbidden_any"])
    )


def select_skill(packages, public_text, trusted_implementations):
    """Return one matching frozen skill, or ``None`` on no/ambiguous match."""
    matches = [
        validate_skill_package(package, trusted_implementations)
        for package in packages
        if recognizer_matches(package, public_text, trusted_implementations)
    ]
    return matches[0] if len(matches) == 1 else None


def apply_skill_library(public_problem, backend_result, packages, *,
                        trusted_implementation_digests, trusted_implementation_functions):
    """Apply one unambiguous verified skill or preserve the backend exactly.

    Function objects come only from the controller-owned registry.  A package
    names a hash-bound entry; it never supplies executable content.  Expected
    local implementation failures are converted to observable abstentions.
    Global interruption and accounting errors must be handled outside this
    pure wrapper and therefore are not caught here.
    """
    public = validate_public_input(public_problem)
    original = deepcopy(backend_result)
    report = {
        "schema": "verified-skill-application-v1",
        "version": VERSION,
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "backend_result_sha256": digest(original),
        "adopted": False,
        "skill_sha256": None,
        "implementation_id": None,
        "compiler_status": "not_applicable",
        "result": original,
    }
    skill = select_skill(packages, public["text"], trusted_implementation_digests)
    if skill is None:
        report["reason"] = "no_unique_verified_skill"
    else:
        implementation_id = skill["implementation"]["id"]
        function = trusted_implementation_functions.get(implementation_id)
        report["skill_sha256"] = digest(skill)
        report["implementation_id"] = implementation_id
        if not callable(function):
            report["reason"] = "trusted_implementation_unavailable"
        else:
            try:
                if skill["schema"] == SKILL_SCHEMA_V2:
                    compiled = function(
                        deepcopy(public), deepcopy(skill["limits"]),
                        deepcopy(skill["implementation"]["configuration"]),
                    )
                else:
                    compiled = function(deepcopy(public), deepcopy(skill["limits"]))
                if not isinstance(compiled, dict):
                    raise InvalidSkill("invalid_trusted_result")
                report["compiler_status"] = compiled.get("status", "unknown")
                if compiled.get("status") == "optimal" and compiled.get("objective") is not None:
                    report["adopted"] = True
                    report["result"] = deepcopy(compiled)
                else:
                    report["reason"] = "trusted_compile_or_solve_not_optimal"
            except (InvalidSkill, ValueError, KeyError, TypeError, ArithmeticError) as exc:
                report["compiler_status"] = "failed_closed"
                report["reason"] = type(exc).__name__
    report["result_sha256"] = digest(report["result"])
    report["fallback_identity"] = (
        not report["adopted"] and report["result_sha256"] == report["backend_result_sha256"]
    )
    return report


def validate_lineage(events, trusted_implementations):
    """Validate a complete immutable promotion lineage in generation order."""
    if not isinstance(events, list):
        raise InvalidSkill("invalid_lineage")
    accepted = {}
    accepted_versions = set()
    previous_event_sha256 = None
    for index, event in enumerate(events, 1):
        _exact_keys(event, {
            "schema", "generation", "previous_event_sha256", "skill", "skill_sha256",
            "static_evidence_sha256", "replay_evidence_sha256", "promotion_evidence_sha256",
            "decision", "event_sha256",
        }, "invalid_promotion_event_fields")
        if event["schema"] != EVENT_SCHEMA or event["generation"] != index:
            raise InvalidSkill("invalid_promotion_generation")
        if event["previous_event_sha256"] != previous_event_sha256:
            raise InvalidSkill("broken_promotion_chain")
        skill = validate_skill_package(event["skill"], trusted_implementations)
        expected_skill_sha256 = digest(skill)
        if event["skill_sha256"] != expected_skill_sha256:
            raise InvalidSkill("skill_digest_mismatch")
        for key in ("static_evidence_sha256", "replay_evidence_sha256", "promotion_evidence_sha256"):
            _sha256(event[key], reason="invalid_" + key)
        if event["decision"] not in {"accepted", "rejected"}:
            raise InvalidSkill("invalid_promotion_decision")
        unsigned = {key: deepcopy(value) for key, value in event.items() if key != "event_sha256"}
        if event["event_sha256"] != digest(unsigned):
            raise InvalidSkill("event_digest_mismatch")
        parent = skill["parent_sha256"]
        if skill["version"] == 1:
            if parent is not None:
                raise InvalidSkill("first_skill_version_has_parent")
        else:
            if parent not in accepted:
                raise InvalidSkill("skill_parent_not_previously_accepted")
            parent_skill = accepted[parent]
            if (parent_skill["skill_id"] != skill["skill_id"]
                    or parent_skill["family"] != skill["family"]
                    or parent_skill["version"] + 1 != skill["version"]):
                raise InvalidSkill("invalid_skill_version_ancestry")
        if event["decision"] == "accepted":
            identity = (skill["skill_id"], skill["version"])
            if identity in accepted_versions:
                raise InvalidSkill("duplicate_accepted_skill_version")
            accepted[expected_skill_sha256] = skill
            accepted_versions.add(identity)
        previous_event_sha256 = event["event_sha256"]
    return {"events": len(events), "accepted_skills": len(accepted),
            "head_event_sha256": previous_event_sha256}


def make_promotion_event(*, generation, previous_event_sha256, skill, trusted_implementations,
                         static_evidence_sha256, replay_evidence_sha256,
                         promotion_evidence_sha256, decision):
    validated = validate_skill_package(skill, trusted_implementations)
    event = {
        "schema": EVENT_SCHEMA,
        "generation": generation,
        "previous_event_sha256": previous_event_sha256,
        "skill": validated,
        "skill_sha256": digest(validated),
        "static_evidence_sha256": static_evidence_sha256,
        "replay_evidence_sha256": replay_evidence_sha256,
        "promotion_evidence_sha256": promotion_evidence_sha256,
        "decision": decision,
    }
    for key in ("static_evidence_sha256", "replay_evidence_sha256", "promotion_evidence_sha256"):
        _sha256(event[key], reason="invalid_" + key)
    if decision not in {"accepted", "rejected"}:
        raise InvalidSkill("invalid_promotion_decision")
    if type(generation) is not int or generation < 1:
        raise InvalidSkill("invalid_promotion_generation")
    _sha256(previous_event_sha256, nullable=True, reason="invalid_previous_event_sha256")
    event["event_sha256"] = digest(event)
    return event


__all__ = [
    "EVENT_SCHEMA", "InvalidSkill", "SKILL_SCHEMA", "SKILL_SCHEMA_V2", "VERSION",
    "apply_skill_library", "make_promotion_event", "recognizer_matches", "select_skill", "skill_sha256",
    "validate_lineage", "validate_skill_package",
]
