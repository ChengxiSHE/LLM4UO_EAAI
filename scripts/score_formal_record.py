"""Separate evaluator; development callers receive only a Boolean proxy score."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.formal_evaluation import grade
from llm4or.benchmark_registry import load_public_registry
from llm4or.run_interruption import require_scoreable_record


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--record',required=True);ap.add_argument('--development',action='store_true')
    args=ap.parse_args();record=json.loads(Path(args.record).read_text());pid=record['problem_id']
    require_scoreable_record(record)
    if args.development:
        split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
        allowed={x for f in split['families'] if f['role'] in {'development_propose','development_select','update_gate'} for x in f['members']}
        if pid not in allowed:raise ValueError('test_label_access_denied')
    public=next(r['public'] for r in load_public_registry(ROOT) if r['id']==pid)
    reference=next(r for r in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records'] if r['problem_id']==pid)
    result=grade(record,public,reference,independent=not args.development)
    print(json.dumps({'score':result['published_proxy_match'] is True} if args.development else result))


if __name__=='__main__':main()
