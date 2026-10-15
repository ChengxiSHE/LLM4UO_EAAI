"""Validate sealed blind reviews, adjudicate disagreements, then unblind aggregate."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.pipeline import write_json

DIRECTORY=ROOT/'results/private/v6_blind_semantic_audit'
OUTPUT=ROOT/'results/v6_blind_semantic_audit_summary.json'
FIELDS=('contract_faithfulness','preferred_complete_model','interface_sufficient','confidence')
CHOICES={
    'contract_faithfulness':{'correct','incorrect','unclear'},
    'preferred_complete_model':{'A','B','both','neither','unclear'},
    'interface_sufficient':{'yes','no','unclear'},
    'confidence':{'high','medium','low'},
}


def file_sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_answers(path,expected,packet_sha):
    data=json.loads(path.read_text())
    if data.get('sealed') is not True or not isinstance(data.get('reviewer_id'),str) or not data['reviewer_id'].strip():
        raise ValueError('review_not_sealed:'+path.name)
    if data.get('packet_sha256')!=packet_sha:raise ValueError('review_packet_mismatch:'+path.name)
    rows=data.get('answers');by_id={r.get('audit_id'):r for r in rows or []}
    if set(by_id)!=expected or len(by_id)!=len(rows):raise ValueError('review_item_mismatch:'+path.name)
    for row in rows:
        if set(row)!={'audit_id',*FIELDS,'rationale'} or not isinstance(row['rationale'],str) or not row['rationale'].strip():
            raise ValueError('review_schema:'+path.name)
        for field in FIELDS:
            if row[field] not in CHOICES[field]:raise ValueError('review_choice:'+field)
    return data,by_id


def score(directory=DIRECTORY,output=OUTPUT,manifest_path=None):
    directory=Path(directory);output=Path(output)
    if output.exists():raise ValueError('blind_audit_already_scored')
    manifest_path=Path(manifest_path) if manifest_path else ROOT/'results/v6_blind_semantic_audit_manifest.json'
    manifest=json.loads(manifest_path.read_text());packet_path=directory/'audit_packet.json';key_path=directory/'audit_key.json'
    if file_sha(packet_path)!=manifest.get('packet_sha256') or file_sha(key_path)!=manifest.get('key_sha256'):
        raise ValueError('blind_audit_binding_mismatch')
    packet_sha=manifest['packet_sha256'];packet=json.loads(packet_path.read_text());expected={x['audit_id'] for x in packet['items']}
    r1,a=load_answers(directory/'reviewer_1_answers.json',expected,packet_sha)
    r2,b=load_answers(directory/'reviewer_2_answers.json',expected,packet_sha)
    if r1['reviewer_id']==r2['reviewer_id']:raise ValueError('reviewers_must_be_distinct')
    disagreements={identifier for identifier in expected if any(a[identifier][f]!=b[identifier][f] for f in FIELDS[:3])}
    adjudicated={}
    if disagreements:
        data=json.loads((directory/'adjudicator_answers.json').read_text())
        if data.get('sealed') is not True or data.get('reviewer_id') in {r1['reviewer_id'],r2['reviewer_id'],None}:
            raise ValueError('independent_adjudicator_required')
        if data.get('packet_sha256')!=packet_sha:raise ValueError('adjudicator_packet_mismatch')
        rows=data.get('answers') or [];adjudicated={r.get('audit_id'):r for r in rows}
        if set(adjudicated)!=disagreements:raise ValueError('adjudication_item_mismatch')
        for row in rows:
            if set(row)!={'audit_id',*FIELDS,'rationale'} or not isinstance(row['rationale'],str) or not row['rationale'].strip():
                raise ValueError('adjudication_schema')
            for field in FIELDS:
                if row[field] not in CHOICES[field]:raise ValueError('adjudication_choice')
    key={x['audit_id']:x for x in json.loads(key_path.read_text())['items']}
    if set(key)!=expected:raise ValueError('audit_key_item_mismatch')
    counts=Counter();families=defaultdict(Counter)
    for identifier in sorted(expected):
        final=adjudicated.get(identifier,a[identifier]);item=key[identifier]
        counts['items']+=1;counts['agreement_without_adjudication']+=identifier not in disagreements
        counts['contract:'+final['contract_faithfulness']]+=1
        counts['interface:'+final['interface_sufficient']]+=1
        if not item['contract_candidate_changed']:continue
        choice=final['preferred_complete_model'];mapped=item['pair_mapping'].get(choice,choice)
        outcome=('improvement' if mapped=='contract_candidate' else 'regression' if mapped=='initial'
                 else 'tie' if mapped=='both' else 'unresolved')
        counts['changed:'+outcome]+=1;families[item['family_id']][outcome]+=1
    family_counts={'changed_operational_families':len(families),
                   'families_with_improvement':sum(v['improvement']>0 for v in families.values()),
                   'families_with_regression':sum(v['regression']>0 for v in families.values())}
    mechanism_success=(counts['contract:incorrect']==0 and family_counts['families_with_improvement']>=5
                       and family_counts['families_with_regression']==0)
    summary={'schema':'v6-blind-semantic-audit-summary-v1','reviewers':2,'adjudicator_used':bool(disagreements),
             'counts':dict(counts),'family_counts':family_counts,
             'targeted_mechanism_success':mechanism_success,
             'overall_benchmark_accuracy_claim_eligible':False,
             'claim_guard':('Blind OR review of all 12 v6-changed pairs across eight operational families. '
                            'A pass supports the targeted domain-repair mechanism, not overall benchmark accuracy; '
                            'operational families are not certified IID.')}
    write_json(output,summary);return summary


def main():
    summary=score();print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
