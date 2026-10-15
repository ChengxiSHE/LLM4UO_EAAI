"""Read-only provenance/count/text-overlap audit; no reference answers or model calls."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.pipeline import write_json


def norm(text):return re.sub(r'\s+',' ',text.strip().casefold())


def main():
    manifests=[json.loads((ROOT/path).read_text()) for path in
               ('data/manifests/source_manifest.json','data/manifests/benchmark_inventory_20260831_sources.json')]
    inventory=[];texts={};checked=0
    for manifest in manifests:
        for r in manifest['records']:
            path=ROOT/r['local_path'];raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('Source changed: '+r['local_path'])
            checked+=1
            if path.suffix not in ('.json','.jsonl'):continue
            if 'nl4opt__nl4opt-competition' in str(path):
                rows=[next(iter(json.loads(line).values())) for line in raw.splitlines() if line.strip()]
                question_field='document'
            else:
                try:rows=json.loads(raw)
                except json.JSONDecodeError:rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
                question_field=next(k for k in ('en_question','Question','question','description') if all(k in row for row in rows))
            # Full JSON containers are parsed; only question text is retained.
            # Target values are not inspected, printed, or used for selection.
            questions=[row[question_field] for row in rows]
            if not all(isinstance(q,str) and q.strip() for q in questions):raise ValueError('Empty question')
            expected=r.get('rows',r.get('top_level_items_or_rows'))
            if expected!=len(questions):raise ValueError('Row count changed')
            normalized=[norm(q) for q in questions]
            texts[r['local_path']]=set(normalized)
            inventory.append({'path':r['local_path'],'repo':r['repo'],'revision':r['revision'],
                              'sha256':r['sha256'],'rows':len(questions),'question_field':question_field,
                              'exact_unique_questions':len(set(normalized)),
                              'whitespace_word_count_median':sorted(len(q.split()) for q in questions)[len(questions)//2],
                              'whitespace_word_count_max':max(len(q.split()) for q in questions)})
    complex_manifest=json.loads((ROOT/'data/manifests/complexor_sources.json').read_text())
    complex_plan=next(b for b in json.loads((ROOT/'experiments/benchmark_plan.json').read_text())['benchmarks']
                      if b['name']=='ComplexOR')
    bundle_records=[{'path':r['upstream_path'],'sha256':r['sha256']} for r in complex_manifest['records']
                    if r['upstream_path'].startswith('dataset/ComplexOR/')]
    bundle_digest=hashlib.sha256(json.dumps(bundle_records,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if bundle_digest!=complex_plan['source']['sha256']:raise ValueError('ComplexOR bundle digest changed')
    complex_texts=[]
    for r in complex_manifest['records']:
        raw=(ROOT/r['local_path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('ComplexOR source changed: '+r['local_path'])
        checked+=1
        if r['upstream_path'].endswith('/input_targets.json'):
            question=json.loads(raw)['description']
            if not isinstance(question,str) or not question.strip():raise ValueError('Empty ComplexOR description')
            complex_texts.append(question)
    if len(complex_texts)!=complex_plan['source_rows_before_split']:raise ValueError('ComplexOR count changed')
    complex_path=complex_plan['source']['local_path']
    texts[complex_path]={norm(q) for q in complex_texts}
    inventory.append({'path':complex_path,'repo':complex_manifest['repo'],'revision':complex_manifest['revision'],
                      'sha256':complex_plan['source']['sha256'],'hash_scope':complex_plan['source']['hash_scope'],
                      'rows':len(complex_texts),'question_field':'input_targets.json:description',
                      'exact_unique_questions':len(texts[complex_path]),
                      'whitespace_word_count_median':sorted(len(q.split()) for q in complex_texts)[len(complex_texts)//2],
                      'whitespace_word_count_max':max(len(q.split()) for q in complex_texts)})
    overlaps=[]
    for left,right in itertools.combinations(sorted(texts),2):
        count=len(texts[left]&texts[right])
        if count:overlaps.append({'left':left,'right':right,'normalized_exact_overlap':count})
    report={'status':'source_and_text_audit_not_locked_test_split','verified_source_files':checked,
            'dataset_files':len(inventory)-1,'dataset_bundles':1,'inventory':inventory,'overlaps':overlaps,
            'reference_labels_used_for_selection':False,'source_code_executed':False,'actual_model_api_calls':0,
            'limitations':['Exact text overlap misses paraphrases and parameter variants.',
                           'No-overlap is not proof of independent semantic families.',
                           'Dataset size is the source-file size, not a finalized experimental denominator.',
                           'Existing 136-record quarantine has not yet been expanded to the new source versions.']}
    write_json(ROOT/'data/manifests/benchmark_inventory_audit.json',report)
    print(json.dumps({'verified_source_files':checked,'dataset_files':len(inventory)-1,'dataset_bundles':1,'overlap_pairs':len(overlaps),'actual_model_api_calls':0}))


if __name__=='__main__':main()
