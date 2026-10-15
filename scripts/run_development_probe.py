"""Run one authorized v3 development probe and close it even on failure.

Reads public text and frozen hashes only, never evaluator labels or reference models.
No automatic retries and no protocol changes after dispatch.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.development_live import AUTH_PATH, RUN_DIR, PUBLIC_PATH, PHASES, PROBLEMS, DevelopmentGateway
from llm4or.gateway import Stopped
from llm4or.live import LiveRequest
from llm4or.pipeline import write_json
from llm4or.schema import digest, loads, validate_public
from llm4or.verified_pipeline import run_verified_problem


def main():
    manifest=loads((RUN_DIR/'manifest.json').read_text())
    gateway=DevelopmentGateway(manifest=manifest)
    problems=[validate_public(loads(line)) for line in PUBLIC_PATH.read_text().splitlines()]
    outcomes=[]
    completed=False
    try:
        for p in problems:
            print('Starting '+p['id'],flush=True)
            result=run_verified_problem(p,gateway,{phase:LiveRequest() for phase in PHASES})
            summary={'problem':p['id'],'status':result['status'],'errors':result['errors'],
                     'gate':result.get('repair_gate',{}),'usage':gateway.summary()}
            outcomes.append(summary)
            print(json.dumps(summary),flush=True)
            with gateway._connect() as con:
                errors=[r['error'] for r in con.execute('SELECT error FROM attempts') if r['error']]
            if errors:
                raise Stopped('transport_or_provider_failure_no_new_problem_dispatched')
        completed=True
        write_json(RUN_DIR/'inference_complete.json',{'problem_ids':list(PROBLEMS),'usage':gateway.summary(),
                                                      'completed_at_utc':datetime.now(timezone.utc).isoformat(),
                                                      'cross_task_evolution':False,'equal_token_comparison':False})
    finally:
        summary=gateway.summary()
        write_json(RUN_DIR/'execution_summary.json',{'inference_complete':completed,'outcomes':outcomes,'usage':summary})
        auth=loads(AUTH_PATH.read_text())
        auth.update(status='completed' if completed else 'stopped',further_api_calls_authorized=False,
                    closed_at_utc=datetime.now(timezone.utc).isoformat(),
                    final_request_count=summary['reserved_attempts_including_failures'])
        write_json(AUTH_PATH,auth)
        write_json(RUN_DIR/'CLOSED.json',{'status':auth['status'],'usage':summary,'closed_at_utc':auth['closed_at_utc']})
        print('Probe closed; total requests: '+str(summary['reserved_attempts_including_failures']),flush=True)


if __name__=='__main__':
    try: main()
    except (Stopped,ValueError) as exc:
        print('Probe stopped: '+str(exc),file=sys.stderr)
        raise SystemExit(1)
