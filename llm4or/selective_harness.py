"""Backend-neutral selective trusted-compilation wrapper."""

from copy import deepcopy

from .benchmark_inputs import payload_sha256, validate_public_input
from .gateway import Stopped
from .schema import digest
from .text2opt_template_compiler import detect_template_family, solve_template_problem


VERSION = "backend-neutral-selective-harness-v1"


def wrap_solve_result(
    public_problem, backend_result, *,
    detector=detect_template_family, compiler=solve_template_problem,
):
    """Adopt a trusted compiled solve or preserve the backend result exactly.

    ``backend_result`` is deliberately opaque to the wrapper.  This makes the
    fallback property independent of whether the backend is Base, BIND, CoE,
    or a later normalized system.
    """
    public = validate_public_input(public_problem)
    original = deepcopy(backend_result)
    report = {
        "schema": "backend-neutral-selective-harness-result-v1",
        "version": VERSION,
        "problem_id": public["id"],
        "public_input_sha256": payload_sha256(public),
        "backend_result_sha256": digest(original),
        "adopted": False,
        "family": None,
        "compiler_status": "not_applicable",
        "result": original,
    }
    try:
        family = detector(public["text"])
        compiled = compiler(public)
        report.update(
            family=family,
            compiler_status=compiled.get("status", "unknown"),
            certificate=compiled.get("certificate"),
        )
        if compiled.get("status") == "optimal":
            report["adopted"] = True
            report["result"] = deepcopy(compiled)
    except Stopped as exc:
        report["reason"] = str(exc)
    report["result_sha256"] = digest(report["result"])
    report["fallback_identity"] = (
        not report["adopted"] and report["result_sha256"] == report["backend_result_sha256"]
    )
    return report


__all__ = ["VERSION", "wrap_solve_result"]
