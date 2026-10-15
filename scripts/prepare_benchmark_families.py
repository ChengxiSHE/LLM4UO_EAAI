"""Propagate known development exposure across every new source version.

Components constrain future splits; lexical non-edges do not certify fresh
semantic families. All benchmark rows remain in the full reporting cohort.
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


def main():
    legacy=public_inventory(ROOT,json.loads((ROOT/'data/manifests/source_manifest.json').read_text()))
    prior=json.loads((ROOT/'data/next_development/family_audit.json').read_text())
    exposed={r['id'] for r in prior['records'] if r['split_status']=='quarantine_development'}
    prior_ids={r['id'] for r in prior['records']}
    if prior_ids!={r['id'] for r in legacy}:raise ValueError('legacy exposure inventory changed')
    benchmarks=load_public_registry(ROOT)
    current=[{'id':r['id'],'text':r['public']['text']} for r in benchmarks]
    all_records=legacy+current
    components,membership,edges=group_candidates(all_records,threshold=.86)
    quarantine={membership[x] for x in exposed}
    by_id={r['id']:r for r in benchmarks}
    rows=[dict(id=r['id'],benchmark=r['benchmark'],input_sha256=r['input_sha256'],component=membership[r['id']],
               exposure='known_development_or_candidate_review_overlap' if membership[r['id']] in quarantine else 'no_known_overlap_not_proof_of_unseen',
               full_reporting_cohort=True,eligible_for_locked_test=False,
               family_review_status='requires_semantic_review',reference_curation_exposure=r['benchmark']=='ComplexOR') for r in benchmarks]
    for component in components:
        component['quarantined']=component['id'] in quarantine
        component['benchmark_members']=[x for x in component['members'] if x in by_id]
    report=dict(schema='benchmark-family-isolation-v1',status='exposure_propagated_split_candidates_not_certified_independence',
                source_records=len(rows),all_public_records=len(all_records),records=rows,components=components,edges=edges,
                known_exposed_legacy_records=len(exposed),
                quarantined_benchmark_records=sum(r['exposure'].startswith('known_') for r in rows),
                benchmark_component_count=len({r['component'] for r in rows}),
                by_benchmark={b:dict(Counter(r['exposure'] for r in rows if r['benchmark']==b)) for b in sorted({r['benchmark'] for r in rows})},
                certified_fresh_families=0,locked_independent_test_denominator=None,
                full_reporting_cohort_sha256=digest([{k:r[k] for k in ('id','input_sha256','component')} for r in rows]),
                labels_used_for_grouping=False,actual_model_api_calls=0)
    write_json(ROOT/'data/manifests/benchmark_family_isolation.json',report)
    print(json.dumps({k:report[k] for k in ('source_records','all_public_records','known_exposed_legacy_records','quarantined_benchmark_records','benchmark_component_count','certified_fresh_families','by_benchmark')}))


if __name__=='__main__':main()
