"""Freeze a development-only v4 diagnostic cohort from internal disagreements.

Selection reads public split roles and historical inference payloads, never
evaluation labels, reference answers, or response bodies.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.pipeline import write_json
from llm4or.semantic_decision import build_catalog


def sha256(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source=ROOT/'results/private/formal_v3_20260912'
    split_path=ROOT/'experiments/family_split_v1.json';split=json.loads(split_path.read_text())
    metadata={r['id']:r for r in load_public_registry(ROOT)}
    roles={member:f['role'] for f in split['families'] for member in f['members']}
    families={member:f['id'] for f in split['families'] for member in f['members']}
    evidence=defaultdict(lambda:{'kinds':set(),'candidate_observations':0})
    for path in sorted((source/'request_payloads').glob('*.json')):
        saved=json.loads(path.read_text());payload=json.loads(saved['body']['messages'][1]['content']);context=payload.get('context',{})
        if set(context)!={'initial','teacher','evidence','input_sha256','model_hashes','quote_spans'}:continue
        pid=payload['problem']['id']
        if roles.get(pid) not in {'development_propose','development_select'}:continue
        catalog=build_catalog(payload['problem'],context['initial'],context['teacher'],context['evidence'])
        if catalog['candidates']:
            evidence[pid]['candidate_observations']+=len(catalog['candidates'])
            evidence[pid]['kinds'].update(item['edit']['kind'] for item in catalog['candidates'])
    by_family=defaultdict(list)
    for pid in evidence:by_family[families[pid]].append(pid)
    selected=[]
    for family in sorted(by_family):
        pid=sorted(by_family[family])[0];record=metadata[pid]
        selected.append({'problem_id':pid,'family_id':family,'role':roles[pid],'benchmark':record['benchmark'],
                         'input_sha256':record['input_sha256'],'historical_candidate_kinds':sorted(evidence[pid]['kinds']),
                         'historical_candidate_observations':evidence[pid]['candidate_observations']})
    report={'schema':'v4-development-pilot-selection-v1','status':'frozen_pending_authorization',
            'source_run':'results/private/formal_v3_20260912','source_ledger_sha256':sha256(source/'requests.sqlite3'),
            'family_split_sha256':sha256(split_path),'records':selected,'problem_count':len(selected),
            'family_count':len({r['family_id'] for r in selected}),
            'selection_rule':('Use development_propose/development_select records only; require at least one controller-enumerable '
                              'historical executable difference; choose the lexicographically first problem per operational family.'),
            'labels_or_references_read_for_selection':False,'locked_test_records':0,
            'claim_guard':'This evidence-enriched development cohort is diagnostic and cannot estimate population accuracy.'}
    write_json(ROOT/'experiments/v4_development_pilot_selection.json',report)
    print(json.dumps({'problems':report['problem_count'],'families':report['family_count'],
                      'benchmarks':sorted({r['benchmark'] for r in selected})}))


if __name__=='__main__':main()
