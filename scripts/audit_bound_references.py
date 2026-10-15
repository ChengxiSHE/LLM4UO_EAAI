"""Read native references only after public transcriptions are frozen.

Only counts and unresolved reasons are printed. Values stay evaluator-only.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry,checked_json
from llm4or.reference_audit import parse_native
from llm4or.schema import digest
from llm4or.pipeline import write_json


def main():
    public=load_public_registry(ROOT)
    frozen=ROOT/'data/evaluation/reference_transcriptions_v1.json'
    frozen_hash=hashlib.sha256(frozen.read_bytes()).hexdigest()
    prepared=json.loads((ROOT/'data/evaluation/reference_models_v1.json').read_text())
    models={r['problem_id']:r for r in prepared['records']}
    originals={r['problem_id']:r for r in json.loads(frozen.read_text())['records']}
    for pid,r in models.items():
        if r['model_sha256']!=digest(r['model']) or r['model_sha256']!=digest(originals[pid]['model']) or r['model_sha256']!=originals[pid]['model_sha256'] or r['input_sha256']!=originals[pid]['input_sha256']:
            raise ValueError('reference transcription changed before audit')
    source_manifest=json.loads((ROOT/'data/manifests/complexor_sources.json').read_text())
    hashes={r['local_path']:r['sha256'] for r in source_manifest['records']}
    cache={}; results=[]
    for r in public:
        s=r['source']; i=r['source_index']; is_complex=r['benchmark']=='ComplexOR'
        if is_complex:
            path=s['local_path']+'/'+r['id'].removeprefix('complexor_')+'/data.json'
            expected=hashes[path]; rows=checked_json(ROOT,path,expected); value=rows[0]['output']; selector='0.output'
            if len(rows)!=1 or rows[0]['input']!=r['public']['instances'][0]['input']:raise ValueError('instance binding mismatch')
        else:
            path=s['local_path'];expected=s['sha256']
            if path not in cache:
                raw=(ROOT/path).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('source hash mismatch')
                try:cache[path]=json.loads(raw)
                except json.JSONDecodeError:cache[path]=[json.loads(x) for x in raw.splitlines() if x.strip()]
            field='results' if r['benchmark']=='OptiBench' else 'en_answer'
            value=cache[path][i].get(field);selector=str(i)+'.'+field
        native=parse_native(value,singleton_list=is_complex)
        result=dict(problem_id=r['id'],benchmark=r['benchmark'],input_sha256=r['input_sha256'],input_revision=r['input_revision'],
                    input_status=r['input_status'],source_binding=dict(path=path,sha256=expected,selector=selector),native=native,
                    audit_status='native_parsed_not_independently_certified' if native['parse_status']=='parsed' else 'native_parse_unresolved',
                    denominator_included=True)
        if r['id'] in models:
            reference=models[r['id']]
            if reference['input_sha256']!=r['input_sha256']:raise ValueError('reference input changed')
            result.update({k:v for k,v in reference.items() if k not in {'schema','audit_status'}})
            result['certificate_binding']=digest({'model':result['model'],'solve':result['solve'],'certificate':result['independent_certificate']})
            state=reference['solve']; agree=None
            if native['parse_status']=='parsed' and reference['independent_certificate']['verified']:
                agree=native['status']==state['status']
                if agree and native['status']=='optimal':agree=math.isclose(native['objective'],state['objective'],rel_tol=1e-6,abs_tol=1e-6)
            result['native_agrees_with_transcription']=agree
            result['audit_status']='numeric_transcription_and_native_label_agree' if agree is True else 'reference_conflict' if agree is False else 'reference_comparison_unresolved'
        if r['input_status']!='ready': result['audit_status']='input_ambiguity'
        results.append(result)
    report=dict(schema='bound-benchmark-reference-audit-v1',records=results,source_records=len(results),
                counts=dict(Counter(r['audit_status'] for r in results)),
                by_benchmark={b:dict(Counter(r['audit_status'] for r in results if r['benchmark']==b)) for b in sorted({r['benchmark'] for r in results})},
                public_transcriptions_frozen_before_native_read_sha256=frozen_hash,
                parsed_source_labels_are_not_gold=True,actual_model_api_calls=0)
    write_json(ROOT/'data/evaluation/bound_reference_audit_v1.json',report)
    summary={k:v for k,v in report.items() if k!='records'}
    summary['issues']=[{k:r[k] for k in ('problem_id','audit_status','input_sha256')} for r in results if r['audit_status'] in {'input_ambiguity','reference_conflict'}]
    write_json(ROOT/'data/manifests/reference_readiness_summary.json',summary)
    print(json.dumps(summary['counts']))


if __name__=='__main__':main()
