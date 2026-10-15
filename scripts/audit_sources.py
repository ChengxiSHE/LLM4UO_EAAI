"""Audit downloaded public snapshots without executing their reference programs."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def canonical(text):
    return re.sub(r'\s+', ' ', text.strip().lower())


def main():
    manifest = json.loads((ROOT / 'data/manifests/source_manifest.json').read_text())
    assert not manifest['failures'], 'Resolve download failures first'
    stats, text_sets = [], {}
    for record in manifest['records']:
        path = ROOT / record['local_path']
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == record['sha256'], path
        if path.suffix not in {'.json', '.jsonl'}:
            continue
        if path.suffix == '.jsonl':
            wrapped = [json.loads(line) for line in raw.splitlines() if line.strip()]
            rows = [next(iter(item.values())) for item in wrapped]
            text_key = 'document'
        else:
            rows = json.loads(raw)
            assert isinstance(rows, list)
            text_key = 'description' if 'description' in rows[0] else 'question'
        texts = [canonical(row.get(text_key, '')) for row in rows]
        label = record['repo'] + ':' + record['upstream_path']
        text_sets[label] = set(texts) - {''}
        stats.append({'source': label, 'rows': len(rows),
            'empty_prompts': sum(not s for s in texts),
            'duplicate_prompt_rows_exact_normalized': len(texts) - len(set(texts)),
            'schema_fields': sorted(set().union(*(set(r) for r in rows))),
            'question_field': text_key,
            'type_counts': dict(Counter(r['type'] for r in rows if 'type' in r)),
            'rows_with_reference_program': sum(bool(r.get('correct_program')) for r in rows),
            'rows_with_nonempty_prior_insights': sum(bool(r.get('retrieved_insights')) for r in rows)})
    overlaps = []
    keys = list(text_sets)
    for i, left in enumerate(keys):
        for right in keys[i+1:]:
            n = len(text_sets[left] & text_sets[right])
            if n:
                overlaps.append({'left': left, 'right': right, 'exact_normalized_overlap': n})
    report = {'status': 'metadata_and_integrity_only_not_gold_label_validation',
        'all_file_hashes_match': True, 'datasets': stats, 'exact_overlaps': overlaps,
        'warnings': ['Exact text matching does not detect paraphrases or shared problem templates.',
                     'All answers, formulations, reference code and prior evaluation fields must be evaluator-only.',
                     'No benchmark reference code has been executed or trusted as expert gold.',
                     'Solver and LP/MILP eligibility must be assessed before freezing inclusion lists.']}
    (ROOT / 'data/manifests/audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({'hashes_match': True, 'dataset_files': len(stats), 'overlap_pairs': len(overlaps)}))


if __name__ == '__main__':
    main()
