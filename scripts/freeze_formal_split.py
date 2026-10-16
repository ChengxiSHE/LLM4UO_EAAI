"""Freeze label-blind operational family blocks, never certify statistical iid.

Transitive closure includes the entire legacy inventory, numerical variants,
reviewed named families and a MORE conservative lexical threshold than v1.
This is an operational grouping audit; the remaining semantic/contamination
risk is explicit and limits every inferential claim made from these blocks.
"""
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.families import public_inventory,group_candidates
from llm4or.pipeline import write_json
from llm4or.schema import digest
from llm4or.semantic_families import merge_semantic_templates


def main():
    current=load_public_registry(ROOT);byid={r['id']:r for r in current}
    legacy=public_inventory(ROOT,json.loads((ROOT/'data/manifests/source_manifest.json').read_text()))
    exposed={r['id'] for r in json.loads((ROOT/'data/next_development/family_audit.json').read_text())['records'] if r['split_status']=='quarantine_development'}
    inventory=legacy+[{'id':r['id'],'text':r['public']['text']} for r in current]
    components,membership,edges=group_candidates(inventory,threshold=.70)
    components,membership,edges,reviews=merge_semantic_templates(inventory,components,edges)
    quarantined={membership[x] for x in exposed}
    families=[]
    for f in components:
        members=sorted(x for x in f['members'] if x in byid)
        if not members:continue
        h=int(digest({'split_seed':20260831,'family':f['id']})[:8],16)%100
        role=('quarantine' if f['id'] in quarantined else 'development_propose' if h<10 else
              'development_select' if h<20 else 'update_gate' if h<40 else 'locked_test')
        # Choice of representative depends only on the fixed group and seed,
        # not label availability, difficulty, performance or source preference.
        representative=min(members,key=lambda x:digest({'representative_seed':1731,'id':x}))
        families.append({'id':f['id'],'members':members,'all_version_members':f['members'],'role':role,
                         'representative':representative,'review_note':'rule-audited operational component; not exhaustive expert semantic certification'})
    byrole={role:sorted([f for f in families if f['role']==role],key=lambda f:digest({'order_seed':317,'id':f['id']}))
            for role in {'development_propose','development_select','update_gate','locked_test','quarantine'}}
    if any(len(byrole[r])<n for r,n in [('development_propose',12),('development_select',12),('update_gate',48)]):raise ValueError('insufficient_operational_families')
    schedules={'build':[f['representative'] for f in byrole['development_propose'][:12]],
               'select':[f['representative'] for f in byrole['development_select'][:12]],
               'gate':[[f['id'] for f in byrole['update_gate'][k*24:(k+1)*24]] for k in range(2)]}
    manifest={'schema':'operational-family-split-v1','families':families,'schedules':schedules,
              'labels_used':False,'model_calls':0,'review_status':'grouping_rules_and_cross_split_edges_audited',
              'semantic_independence_certified':False,'statistical_claim':'empirical_gate_only; binomial risk guarantee conditional on unverified semantic independence and reliable proxy labels',
              'grouping':'public-text transitive closure: 23 broad semantic templates, normalized/number-masked exact, named semantic anchors, TF-IDF word/bigram >=0.70; ambiguous multi-template groups merge completely',
              'remaining_risk':'unnamed semantic paraphrases may evade lexical grouping; no claim that all test records are independently unseen',
              'counts':{'records':len(current),'families':len(families),'records_by_role':dict(Counter(f['role'] for f in families for _ in f['members'])),
                        'families_by_role':{k:len(v) for k,v in byrole.items()}},
              'source_inputs_sha256':digest({r['id']:r['input_sha256'] for r in current})}
    write_json(ROOT/'experiments/family_split_v1.json',manifest)
    write_json(ROOT/'data/manifests/formal_family_edges_v1.json',{'edges':edges,'template_reviews':reviews,'split_sha256':digest(manifest)})
    print(json.dumps(manifest['counts']))


if __name__=='__main__':main()
