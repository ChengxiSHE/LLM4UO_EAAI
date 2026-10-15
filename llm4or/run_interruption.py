"""Run-level failures must never become model scores or rejected proposals."""
from functools import wraps
from .gateway import Stopped


class RunInterrupted(Stopped):
    """Abort orchestration while preserving the unique ledger and checkpoints."""


def interrupts_run(reason):
    if not isinstance(reason, str):
        return False
    return reason.startswith((
        'transport_', 'http_', 'provider_', 'codex_cli_', 'global_', 'formal_private_profile_',
        'frozen_file_changed', 'prior_attempt_reserved', 'prior_infrastructure_attempt:',
        'new_full_run_approval_required', 'run_time_limit',
        'request_timeout_outcome_unknown', 'resumed_request_content_drift',
        'cache_integrity_failure', 'tool_cache_corrupted', 'inference_cache_changed',
        'score_binding_changed', 'another_request_active',
    )) or reason in {
        # Legacy worker messages and parent-side pipe/socket exceptions.
        'URLError', 'TimeoutError', 'ConnectionError', 'ConnectionResetError',
        'ConnectionAbortedError', 'ConnectionRefusedError', 'BrokenPipeError',
        'EOFError', 'OSError', 'gaierror', 'SSLError', 'SSLEOFError',
    }


def propagate_interruption(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Stopped as exc:
            if interrupts_run(str(exc)):
                raise RunInterrupted(str(exc)) from None
            raise
    return wrapped


def interrupted_record(record):
    """Also reject legacy cached records created before typed propagation."""
    errors=[str(e.get('reason','')) for e in record.get('errors', [])]
    trace_errors=[str(e.get('error','')) for e in record.get('trace', []) if e.get('error')]
    unavailable=[reason.split('request_unavailable:',1)[1] for reason in errors
                 if reason.startswith('request_unavailable:')]
    # Older shared-cache runs wrapped local provider outcomes (invalid JSON or
    # incomplete output) as request_unavailable for later consumers. Those are
    # model outcomes, not transport loss, and must remain evaluation-eligible.
    if unavailable:
        return any(interrupts_run(reason) for reason in unavailable) or any(
            interrupts_run(reason) for reason in errors+trace_errors
            if not reason.startswith('request_unavailable:'))
    return record.get('status') in {'run_interrupted','infrastructure_unavailable'} or any(
        interrupts_run(reason) for reason in errors+trace_errors)


def require_scoreable_record(record):
    if interrupted_record(record):
        raise RunInterrupted('global_infrastructure_interrupted_record')
