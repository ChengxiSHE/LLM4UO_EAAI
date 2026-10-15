"""Prepare a blinded, reference-free semantic-contract audit packet."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import random
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_contracts import derive_contracts,synthesize_contract_repairs

OUT=ROOT/'results/private/v5_blind_semantic_audit'
MANIFEST=ROOT/'results/v5_blind_semantic_audit_manifest.json'


def main():
    if OUT.exists() or MANIFEST.exists():raise ValueError('blind_audit_already_prepared')
    OUT.mkdir(parents=True)
    public={r['id']:r['public'] for r in load_public_registry(ROOT)}
    split=json.loads((ROOT/'experiments/family_split_v1.json').read_text())
    role={pid:f['role'] for f in split['families'] for pid in f['members']}
    family={pid:f['id'] for f in split['families'] for pid in f['members']}
    complete=json.loads((ROOT/'results/private/formal_v3_20260912/inference_complete.json').read_text())
    cells=[c for c in complete['cells'] if c['method']=='Base' and c['replicate']==17 and c['token_cap']==65536
           and role.get(c['id'])=='locked_test']
    secret=os.urandom(32);rng=random.Random(int.from_bytes(secret,'big'));packet=[];key=[]
    for cell in sorted(cells,key=lambda x:x['id']):
        record=json.loads(Path(cell['record_path']).read_text());initial=record.get('final_model')
        if initial is None:continue
        contracts=derive_contracts(public[cell['id']],initial)
        if not contracts['contracts']:continue
        repaired,repair=synthesize_contract_repairs(public[cell['id']],initial,contracts)
        solvable=execute({'op':'solve','model':repaired}).get('status')=='optimal' if repair['edits'] else True
        left,right=deepcopy(initial),deepcopy(repaired);mapping={'A':'initial','B':'contract_candidate'}
        if rng.getrandbits(1):left,right=right,left;mapping={'A':'contract_candidate','B':'initial'}
        opaque='audit_'+hashlib.sha256(secret+cell['id'].encode()).hexdigest()[:12]
        visible_contracts=[]
        for contract in contracts['contracts']:
            visible={k:deepcopy(v) for k,v in contract.items() if k not in {'source'}}
            visible_contracts.append(visible)
        packet.append({'audit_id':opaque,'public_input':public[cell['id']],
                       'proposed_semantic_contracts':visible_contracts,
                       'candidate_A':left,'candidate_B':right,
                       'questions':{
                           'contract_faithfulness':'correct|incorrect|unclear',
                           'preferred_complete_model':'A|B|both|neither|unclear',
                           'interface_sufficient':'yes|no|unclear',
                           'confidence':'high|medium|low',
                           'rationale':'Cite the exact public clause and algebra/domain reasoning; do not use benchmark answers.',
                       }})
        key.append({'audit_id':opaque,'problem_id':cell['id'],'family_id':family[cell['id']],
                    'source_record_sha256':cell['record_sha256'],'pair_mapping':mapping,
                    'contract_candidate_changed':digest(initial)!=digest(repaired),
                    'contract_candidate_solver_optimal':solvable,
                    'contracts_sha256':contracts['contracts_sha256']})
    instructions={
        'schema':'v5-blind-semantic-audit-v1','reviewer_requirement':'Two OR reviewers who did not design v5; third reviewer adjudicates disagreements.',
        'independence':'Do not consult published objectives, source answers, repository evaluation files, or the private key.',
        'unit':'One audit item; family-level aggregation occurs only after independent labels are sealed.',
        'rubric':[
            'Judge whether each proposed contract follows from the quoted public language and declared business meanings.',
            'Judge the entire A/B formulations, not only solver feasibility or objective value.',
            'Use unclear when the wording or interface cannot determine the answer.',
            'Return one answer object per audit_id without changing packet contents.',
        ],
        'answer_schema':{'audit_id':'string','contract_faithfulness':'correct|incorrect|unclear',
                         'preferred_complete_model':'A|B|both|neither|unclear','interface_sufficient':'yes|no|unclear',
                         'confidence':'high|medium|low','rationale':'string'},
    }
    write_json(OUT/'audit_packet.json',{'instructions':instructions,'items':packet})
    write_json(OUT/'audit_key.json',{'secret_sha256':hashlib.sha256(secret).hexdigest(),'items':key})
    packet_sha=hashlib.sha256((OUT/'audit_packet.json').read_bytes()).hexdigest()
    empty={'reviewer_id':None,'packet_sha256':packet_sha,'sealed':False,'answers':[]}
    write_json(OUT/'reviewer_1_answers.json',empty)
    write_json(OUT/'reviewer_2_answers.json',empty)
    write_json(OUT/'adjudicator_answers.json',empty)
    manifest={'schema':'v5-blind-semantic-audit-manifest-v1','prepared_at':datetime.now(timezone.utc).isoformat(),
              'items':len(packet),'operational_families':len({x['family_id'] for x in key}),
              'changed_pairs':sum(x['contract_candidate_changed'] for x in key),
              'packet_sha256':packet_sha,
              'key_sha256':hashlib.sha256((OUT/'audit_key.json').read_bytes()).hexdigest(),
              'references_in_packet':False,'new_api_requests':0,
              'status':'prepared_waiting_for_two_independent_or_reviewers'}
    write_json(MANIFEST,manifest);print(json.dumps(manifest,sort_keys=True))


if __name__=='__main__':main()
