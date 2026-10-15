"""Copy and rebind an interrupted formal checkpoint to the current reviewed plan."""
import argparse
import json
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formal_gateway import VERSION, failure_class
from llm4or.pipeline import write_json
from llm4or.schema import canonical,digest


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',default='results/private/formal_v1_20260831');args=ap.parse_args()
    source=(ROOT/args.source).resolve();plan=json.loads((ROOT/'experiments/full_run_plan.json').read_text())
    target=(ROOT/plan['run_directory']).resolve()
    if not (source/'interrupted.json').exists() or not (source/'requests.sqlite3').exists():raise ValueError('source_not_interrupted_ledger')
    if target.exists():raise ValueError('target_already_exists')
    target.mkdir(parents=True,mode=0o700)
    for name in ['requests.sqlite3','request_payloads','inference','evolution','tool_cache']:
        src=source/name
        if src.is_dir():shutil.copytree(src,target/name)
        elif src.is_file():shutil.copy2(src,target/name)
    config={'version':VERSION,'plan':digest(plan),'offline':False,'directory':str(target)}
    with sqlite3.connect(target/'requests.sqlite3') as db:
        old=json.loads(db.execute('SELECT config FROM metadata WHERE id=1').fetchone()[0])
        if old.get('offline') is not False:raise ValueError('source_not_live')
        halt=db.execute('SELECT reason FROM halt WHERE id=1').fetchone()
        if halt and failure_class(halt[0])=='retryable':db.execute('DELETE FROM halt WHERE id=1')
        db.execute('UPDATE metadata SET config=? WHERE id=1',(canonical(config),))
        statuses=dict(db.execute('SELECT status,count(*) FROM attempts GROUP BY status'))
        totals=db.execute('SELECT physical_calls,physical_tokens,logical_calls,logical_tokens FROM totals WHERE id=1').fetchone()
    write_json(target/'checkpoint_migration.json',{'schema':'formal-checkpoint-migration-v1','source':str(source),
        'source_plan_sha256':old.get('plan'),'target_plan_sha256':digest(plan),'attempt_statuses_preserved':statuses,
        'ledger_totals_preserved':dict(zip(['physical_calls','physical_tokens','logical_calls','logical_tokens'],totals)),
        'reserved_attempts_resume_under_bounded_retry':True,
        'note':'No API request was made. Existing reservations, responses, payloads, tool caches and inference checkpoints were copied.'})
    print(json.dumps({'status':'migrated','target':str(target),'new_api_requests':0}))


if __name__=='__main__':main()
