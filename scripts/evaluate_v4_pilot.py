"""Evaluate a closed v4 development diagnostic; never runs during inference."""
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.formal_evaluation import grade
from llm4or.pipeline import write_json
from llm4or.schema import digest


def main():
    plan=json.loads((ROOT/'experiments/v4_development_pilot_plan.json').read_text())
    auth=json.loads((ROOT/'experiments/v4_development_pilot_authorization.json').read_text())
    if auth['status']!='completed' or auth['plan_sha256']!=digest(plan):raise ValueError('inference_not_closed')
    directory=ROOT/plan['run_directory'];complete=json.loads((directory/'inference_complete.json').read_text())
    public={r['id']:r['public'] for r in load_public_registry(ROOT)}
    references={r['problem_id']:r for r in json.loads((ROOT/'data/evaluation/bound_reference_audit_v1.json').read_text())['records']}
    records={}
    for cell in complete['cells']:
        saved=json.loads(Path(cell['record_path']).read_text());record=saved['record']
        if digest(record)!=cell['record_sha256']:raise ValueError('record_changed')
        records[(cell['method'],cell['problem_id'])]=record
    counts=Counter();error_reasons=Counter();rows=[]
    for selected in plan['selection']['records']:
        pid=selected['problem_id'];base=records[('Base',pid)];method=records[('A-v4',pid)]
        b=grade(base,public[pid],references[pid],independent=False).get('published_proxy_match')
        a=grade(method,public[pid],references[pid],independent=False).get('published_proxy_match')
        if b in {True,False} and a in {True,False}:
            counts['paired_known']+=1;counts['correction' if a and not b else 'regression' if b and not a
                else 'both_match' if b else 'neither_match']+=1
        trace=method.get('trace',[]);semantic=trace[0] if trace else {}
        counts['initial_supported']+=method.get('final_model') is not None
        catalog=semantic.get('candidate_catalog',{});counts['catalog_with_candidates']+=bool(catalog.get('candidates'))
        packet=semantic.get('teacher_packet',{});counts['repair_packet']+=packet.get('status')=='repair'
        gate=semantic.get('gate',{});counts['accepted_repair']+=gate.get('status')=='accepted_relative_to_evidence'
        counts['actual_model_change']+=semantic.get('before_hash')!=semantic.get('after_hash')
        for error in method.get('errors',[]):error_reasons[error.get('reason','unknown')]+=1
        rows.append({'problem_id':pid,'family_id':selected['family_id'],'benchmark':selected['benchmark'],
                     'base_proxy_match':b,'a_v4_proxy_match':a,'a_v4_status':method.get('status'),
                     'catalog_candidates':len(catalog.get('candidates',[])),'packet_status':packet.get('status'),
                     'gate_status':gate.get('status'),'changed':semantic.get('before_hash')!=semantic.get('after_hash')})
    report={'schema':'v4-development-pilot-evaluation-v1','plan_sha256':digest(plan),'development_only':True,
            'counts':dict(counts),'error_reasons':dict(error_reasons),'records':rows,'usage':complete['usage'],
            'success_rule':('Promising only if actionable yield opens and paired development corrections exceed regressions; '
                            'a confirmatory claim still requires frozen untouched families and formulation-level gold.'),
            'claim_guard':'Evidence-enriched development results are diagnostic, not a held-out accuracy estimate.'}
    write_json(directory/'evaluation.json',report);write_json(ROOT/'results/v4_development_pilot_summary.json',{k:v for k,v in report.items() if k!='records'})
    print(json.dumps({k:report[k] for k in ('counts','error_reasons','usage')}))


if __name__=='__main__':main()
