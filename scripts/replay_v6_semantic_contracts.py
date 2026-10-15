"""Compare frozen v5 and candidate v6 contracts on development roles only."""
from collections import Counter,defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_contracts import apply_contracts_transactionally,derive_contracts as derive_v1
from llm4or.semantic_contracts_v2 import derive_contracts as derive_v2

SOURCE=ROOT/'results/private/formal_v3_20260912'
OUTPUT=ROOT/'results/mechanism_v6_development_replay.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def classify(before,after):
    if before not in {True,False} or after not in {True,False}:return 'unknown'
    if after and not before:return 'correction'
    if before and not after:return 'regression'
    return 'both_match' if before else 'neither_match'


def main():
    if OUTPUT.exists():raise ValueError('v6_development_replay_already_exists')
    registry={r['id']:r['public'] for r in load_public_registry(ROOT)}
    references={r['problem_id']:r for r in json.loads(
        (ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    roles={pid:f['role'] for f in split['families'] for pid in f['members']}
    families={pid:f['id'] for f in split['families'] for pid in f['members']}
    complete=json.loads((SOURCE/'inference_complete.json').read_text())
    cells={c['id']:c for c in complete['cells'] if c['method']=='Base' and c['replicate']==17
           and c['token_cap']==65536 and roles.get(c['id']) in {'development_propose','development_select'}}
    summaries={};effects_by_version={}
    for name,derive in [('v5',derive_v1),('v6',derive_v2)]:
        counts=Counter();effects=defaultdict(Counter)
        for pid,cell in sorted(cells.items()):
            counts['records']+=1;record=json.loads(Path(cell['record_path']).read_text())
            initial=record.get('final_model')
            if initial is None:counts['no_model']+=1;continue
            contracts=derive(registry[pid],initial)
            if not contracts['contracts']:continue
            counts['contract_triggered']+=1
            for contract in contracts['contracts']:counts['contract:'+contract['source']]+=1
            repaired,report=apply_contracts_transactionally(registry[pid],initial,execute,contracts)
            counts['status:'+report['status']]+=1
            if digest(repaired)==digest(initial):continue
            counts['actual_model_change']+=1
            base=grade(record,registry[pid],references[pid],independent=False).get('published_proxy_match')
            replay={**deepcopy(record),'final_model':repaired,
                    'final_solve':execute({'op':'solve','model':repaired}),'status':'completed'}
            updated=grade(replay,registry[pid],references[pid],independent=False).get('published_proxy_match')
            outcome=classify(base,updated);counts['transition:'+outcome]+=1;effects[families[pid]][outcome]+=1
        summaries[name]=dict(counts)
        effects_by_version[name]={
            'changed_operational_families':len(effects),
            'families_with_correction':sum(v['correction']>0 for v in effects.values()),
            'families_with_regression':sum(v['regression']>0 for v in effects.values()),
        }
    report={
        'schema':'v6-semantic-contract-development-replay-v1','development_only':True,
        'method':'Base+SemanticContracts-v2','source_method':'Base','replicate':17,'token_cap':65536,
        'source_inference_sha256':sha(SOURCE/'inference_complete.json'),
        'semantic_contracts_v1_sha256':sha(ROOT/'llm4or/semantic_contracts.py'),
        'semantic_contracts_v2_sha256':sha(ROOT/'llm4or/semantic_contracts_v2.py'),
        'summaries':summaries,'family_effects':effects_by_version,'new_api_requests':0,
        'promising':(summaries['v6'].get('transition:correction',0)>summaries['v5'].get('transition:correction',0)
                     and summaries['v6'].get('transition:regression',0)==0),
        'claim_guard':('Post-hoc development replay selected after inspecting development outcomes. '
                       'It measures mechanism progress, not held-out or confirmatory performance.'),
    }
    write_json(OUTPUT,report);print(json.dumps(report,sort_keys=True))


if __name__=='__main__':main()
