"""Replay v4 development trajectories through candidate-independent contracts."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_contracts import apply_contracts_transactionally, derive_contracts


def main():
    run=ROOT/'results/private/v4_development_pilot_20260913'
    complete=json.loads((run/'inference_complete.json').read_text())
    evaluation=json.loads((run/'evaluation.json').read_text())
    public={r['id']:r['public'] for r in load_public_registry(ROOT)}
    references={r['problem_id']:r for r in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    prior={r['problem_id']:r for r in evaluation['records']}
    cells={c['problem_id']:c for c in complete['cells'] if c['method']=='A-v4'}
    counts=Counter();contract_counts=Counter();rows=[]
    for pid,cell in sorted(cells.items()):
        record=json.loads(Path(cell['record_path']).read_text())['record']
        if record.get('final_model') is None:
            rows.append({'problem_id':pid,'status':'unresolved','base_proxy_match':prior[pid]['base_proxy_match'],
                         'v5_proxy_match':None,'contract_count':0,'contract_edits':0})
            continue
        initial=record['initial_model'];v4_final=record['final_model'];contracts=derive_contracts(public[pid],initial)
        contract_counts['problems_with_contracts']+=bool(contracts['contracts'])
        for contract in contracts['contracts']:contract_counts['contract:'+contract['source']]+=1
        repaired,report=apply_contracts_transactionally(public[pid],v4_final,execute,contracts)
        # If the accepted v4 edit conflicts with a valid contract but the
        # interface cannot realize the full repair, fail closed to the initial
        # formulation rather than keep an unsupported directional change.
        if report['status']=='interface_insufficient' and digest(v4_final)!=digest(initial):
            retained=deepcopy(initial);decision='rollback_v4_edit_interface_insufficient'
        else:
            retained=repaired;decision=report['status']
        replay={**record,'final_model':retained,'final_solve':execute({'op':'solve','model':retained}),
                'status':'completed'}
        score=grade(replay,public[pid],references[pid],independent=False).get('published_proxy_match')
        base=prior[pid]['base_proxy_match']
        if base in {True,False} and score in {True,False}:
            counts['paired_known']+=1
            counts['correction' if score and not base else 'regression' if base and not score
                   else 'both_match' if base else 'neither_match']+=1
        counts['actual_model_change']+=digest(retained)!=digest(initial)
        counts['contract_repair_accepted']+=report['status']=='accepted'
        counts['interface_insufficient']+=report['status']=='interface_insufficient'
        rows.append({'problem_id':pid,'benchmark':prior[pid]['benchmark'],'status':decision,
                     'base_proxy_match':base,'v4_proxy_match':prior[pid]['a_v4_proxy_match'],
                     'v5_proxy_match':score,'contract_count':len(contracts['contracts']),
                     'contract_edits':len(report['edits'])})
    report={'schema':'v5-semantic-contract-offline-replay-v1','development_only':True,
            'source_plan_sha256':evaluation['plan_sha256'],'source_usage':evaluation['usage'],
            'new_api_requests':0,'counts':dict(counts),'contract_counts':dict(contract_counts),'records':rows,
            'success_rule':evaluation['success_rule'],
            'promising':counts['actual_model_change']>0 and counts['correction']>counts['regression'],
            'claim_guard':'Post-hoc development replay; useful for mechanism debugging, not a held-out estimate.'}
    write_json(ROOT/'results/mechanism_v5_offline_replay.json',report)
    print(json.dumps({k:report[k] for k in ('counts','contract_counts','new_api_requests','promising')},sort_keys=True))


if __name__=='__main__':main()
