"""Use ONLY after an explicit user confirmation of this exact frozen scope."""
import argparse
import datetime
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.schema import digest
from llm4or.pipeline import write_json
from scripts.run_formal import preflight


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan-sha256',required=True);ap.add_argument('--user-confirmation',required=True)
    args=ap.parse_args();plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text())
    if args.plan_sha256!=digest(plan) or not args.user_confirmation.strip():raise ValueError('exact_scope_confirmation_required')
    preflight(plan)
    verification=json.loads((ROOT/'results/full_preparation_verification.json').read_text())
    if verification.get('status')!='passed' or verification.get('plan_sha256')!=digest(plan):raise ValueError('current_plan_not_verified')
    path=ROOT/'experiments/full_run_authorization.json';auth=json.loads(path.read_text())
    if auth['status']!='pending' or auth['plan_sha256']!=digest(plan):raise ValueError('cannot_reopen_or_replace_authorization')
    auth.update(status='approved',user_confirmation=args.user_confirmation,
                approved_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write_json(path,auth)
    print(json.dumps({'status':'approved','plan_sha256':digest(plan),'limits':auth['limits']}))


if __name__=='__main__':main()
