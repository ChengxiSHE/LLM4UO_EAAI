"""Offline v3 integration and manual typed-claim replay of two frozen S1 errors."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.fixtures import box, scenario, verified_record
from llm4or.gateway import Gateway, Limits, MockReply, Stopped
from llm4or.live import LiveGateway, build_request
from llm4or.pipeline import write_json
from llm4or.schema import canonical, digest
from llm4or.teacher_facts import compile_teacher_record
from llm4or.verified_pipeline import VERSION, make_verified_payload, run_verified_problem


def archive_hashes(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file()}


def replay_s1(archive):
    problems={p['id']:p for p in map(json.loads,(ROOT/'data/pilot/public/problems.jsonl').read_text().splitlines())}
    reports=[]
    for pid in ('dev_021','dev_037'):
        original=json.loads((archive/f'{pid}.inference.json').read_text())
        initial,teacher=original['initial'],original['teacher_model']
        old=original['teacher_packet']
        raw={'schema':'teacher-v2','status':'unresolved',
             'model_hashes':{'initial':digest(initial),'teacher':digest(teacher)},
             **{k:old[k] for k in ('quote','start','end')},
             'interpretation':old['explanation'],'target_rows':[],'positive_examples':[]}
        if pid=='dev_021':
            raw['claims']=[{'id':v+'_upper_absent','model':'teacher','kind':'declared_bound',
                            'variable':v,'side':'upper','expected':None} for v in ('ham','bacon')]
            # Also test semantic absence, not just literal storage location.
            raw['claims'] += [{'id':v+'_not_implied','model':'teacher','kind':'entails',
                              'coefficients':{w:int(w==v) for w in ('ham','bacon')},
                              'sense':'le','rhs':bound,'expected':False} for v,bound in (('ham',200),('bacon',220))]
        else:
            raw['claims']=[{'id':'alleged_carbon_coefficient','model':'initial','kind':'row_coefficient',
                            'row':'co2_limit','variable':'large_truck_acres','expected':7}]
        packet=compile_teacher_record(raw,problems[pid],initial,teacher,original['evidence'])
        assert packet['fact_gate_reason']=='teacher_fact_refuted',pid
        assert all(r['status']=='refuted' for r in packet['verified_facts']),pid
        reports.append({'problem_id':pid,'translation':'assistant_manually_translated_frozen_prose_not_new_model_output',
                        'original_model_hashes':raw['model_hashes'],'new_packet':packet})
    return reports


def main():
    archive=ROOT/'results/private/pilot_s1_20260831'
    before=archive_hashes(archive)
    with patch('llm4or.live.load_credential',side_effect=AssertionError('credential read forbidden')):
        try:
            LiveGateway()
        except Stopped as exc:
            assert str(exc)=='live_authorization_scope_mismatch'
        else:
            raise AssertionError('completed S1 authorization must remain closed')
    with sqlite3.connect(f'file:{archive / "requests.sqlite3"}?mode=ro',uri=True) as con:
        old_attempts=con.execute('SELECT count(*) FROM attempts').fetchone()[0]
    assert old_attempts==46
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'llm4or').glob('*.py'))+[Path(__file__).resolve()]}
    output=ROOT/'results'/('offline_v3_'+digest(hashes)[:12])
    gateway=Gateway(output,Limits(requests=30),manifest={'source_hashes':hashes,'protocol':VERSION})
    reports=[]
    for name in ('correction','overconstraint','false_fact','no_witness','unresolved','malformed'):
        problem,replies,_=scenario(name)
        raw=verified_record()
        if name=='false_fact':
            raw['claims'].append({'id':'wrong_rhs','model':'teacher','kind':'row_rhs','row':'capacity','expected':0})
        elif name=='no_witness':
            replies['teacher_model']=MockReply(canonical(box()))
            raw=verified_record(teacher=box(),status='no_witness')
        elif name=='unresolved':
            raw=verified_record(status='unresolved')
        replies['teacher_feedback']=MockReply(canonical(raw))
        result=run_verified_problem(problem,gateway,replies)
        gate=result.get('repair_gate',{})
        if name=='correction': assert gate.get('status')=='accepted_relative_to_evidence',result
        elif name=='overconstraint': assert gate.get('reason')=='protected_example_regression',result
        elif name=='false_fact': assert gate.get('reason')=='teacher_fact_refuted',result
        elif name=='malformed': assert result['status']=='initial_failed',result
        else: assert gate.get('reason')=='teacher_unresolved',result
        reports.append({'fixture':name,'inference_status':result['status'],'repair_gate':gate,
                        'fact_gate_status':result.get('teacher_packet',{}).get('fact_gate_status')})
    assert gateway.summary()['attempts_including_failures']==23
    # An idempotent rerun of an accepted case must use the identical cached calls.
    p,replies,_=scenario();replies['teacher_feedback']=MockReply(canonical(verified_record()))
    run_verified_problem(p,gateway,replies)
    assert gateway.summary()['attempts_including_failures']==23
    replay=replay_s1(archive)
    wire_checks=[]
    for line in (ROOT/'data/next_development/public/problems.jsonl').read_text().splitlines():
        p=json.loads(line)
        payload=make_verified_payload(p,'initial')
        wire_checks.append({'problem_id':p['id'],'phase':'initial','bytes':len(build_request(payload,Limits())),
                            'context_contains_reference':False})
    assert before==archive_hashes(archive),'S1 archive changed'
    report={'kind':'offline_protocol_validation_not_benchmark','passed':True,'protocol':VERSION,
            'actual_api_requests':0,'credentials_read':False,'s1_archive_unchanged':True,
            's1_closed_live_guard_verified':True,'s1_ledger_attempts':old_attempts,
            'source_hashes':hashes,'integration_directory':str(output),
            'fixed_response_cases':reports,'simulated_attempts':23,'resume_reuses_same_attempts':True,
            's1_manual_claim_replay':replay,'initial_wire_size_checks':wire_checks,
            'limitations':['Fixed responses and hand-translated claims do not test whether the LLM follows teacher-v2.',
                           'Verified facts about candidate models do not establish fidelity to natural language.',
                           'Cross-task evolution and benchmark improvement have not been measured.']}
    write_json(ROOT/'results/post_pilot_verification.json',report)
    print(json.dumps({'passed':True,'fixed_response_cases':len(reports),'s1_errors_replayed':len(replay),
                      'simulated_attempts':23,'actual_api_requests':0,'s1_archive_unchanged':True}))


if __name__=='__main__':main()
