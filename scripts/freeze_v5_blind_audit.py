"""Freeze the v5 blind-review protocol; never opens the randomization key."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'results/private/v5_blind_semantic_audit'
MANIFEST=ROOT/'results/v5_blind_semantic_audit_manifest.json'
PROTOCOL=ROOT/'experiments/v5_blind_semantic_audit_protocol.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if PROTOCOL.exists():raise ValueError('blind_audit_protocol_already_frozen')
    manifest=json.loads(MANIFEST.read_text());packet=DIRECTORY/'audit_packet.json';key=DIRECTORY/'audit_key.json'
    if sha(packet)!=manifest['packet_sha256'] or sha(key)!=manifest['key_sha256']:
        raise ValueError('blind_audit_manifest_binding_mismatch')
    visible=json.loads(packet.read_text())
    if len(visible.get('items',[]))!=manifest['items'] or 'reference' in json.dumps(visible).lower():
        raise ValueError('visible_packet_scope_changed')
    # Aggregate counts only. Do not read pair mappings or problem identifiers.
    protocol={
        'schema':'v5-blind-semantic-audit-protocol-v1','status':'frozen_waiting_for_independent_reviews',
        'frozen_at':datetime.now(timezone.utc).isoformat(),'items':manifest['items'],
        'operational_families':manifest['operational_families'],'changed_pairs':manifest['changed_pairs'],
        'packet_sha256':manifest['packet_sha256'],'key_sha256':manifest['key_sha256'],
        'reviewer_html_sha256':sha(DIRECTORY/'reviewer_packet.html'),
        'scorer_sha256':sha(ROOT/'scripts/score_v5_blind_audit.py'),
        'renderer_sha256':sha(ROOT/'scripts/render_v5_blind_audit.py'),
        'review_design':{
            'primary_reviewers':2,'reviewers_must_be_distinct':True,
            'reviewers_must_not_have_designed_v5':True,
            'adjudicator_required_for_any_primary_disagreement':True,
            'adjudicator_must_be_distinct':True,'answers_must_be_complete_and_sealed':True,
            'published_answers_and_evaluator_files_forbidden':True,
        },
        'outcomes':{
            'contract_faithfulness':'correct|incorrect|unclear',
            'complete_model_preference':'contract_candidate|initial|both|neither|unclear after unblinding',
            'aggregation_unit':'operational family; descriptive because semantic independence is not certified',
        },
        'prospective_pilot_readiness_rule':(
            'all reviewed contracts contain zero incorrect verdicts, at least one changed operational family '
            'prefers the contract candidate, and zero changed operational families prefer the initial model'),
        'confirmatory_claim_eligible_from_this_audit':False,
        'reason_not_confirmatory':(
            'Only three changed pairs across at most two changed operational families; the split is not expert-certified IID.'),
        'new_api_requests':0,
    }
    PROTOCOL.write_text(json.dumps(protocol,sort_keys=True,separators=(',',':'))+'\n')
    print(json.dumps({'status':'frozen','protocol_sha256':sha(PROTOCOL),'items':protocol['items'],
                      'api_requests':0},sort_keys=True))


if __name__=='__main__':main()
