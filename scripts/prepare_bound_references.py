"""Freeze public-input transcriptions before native reference inspection."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.benchmark_registry import load_public_registry
from llm4or.reference_builders import build_reference,SUPPORTED
from llm4or.reference_certificates import certify_lp,certify_discrete
from llm4or.milp_solver import execute
from llm4or.pipeline import write_json
from llm4or.schema import digest,Invalid


def main():
    prepared=[]; blocked=[]
    for r in load_public_registry(ROOT):
        if r['benchmark']!='ComplexOR' or r['id'].removeprefix('complexor_') not in SUPPORTED:continue
        try: prepared.append(build_reference(r['public']))
        except (Invalid,ZeroDivisionError) as e: blocked.append(dict(id=r['id'],input_sha256=r['input_sha256'],reason=str(e)))
    # Atomic transcriptions freeze BEFORE any source reference output is read.
    write_json(ROOT/'data/evaluation/reference_transcriptions_v1.json',dict(schema='reference-transcriptions-v1',records=prepared,blocked=blocked,native_reference_values_used=False))
    checked=[]
    for r in prepared:
        m=r['model']; state=execute({'op':'solve','model':m})
        cert=certify_lp(m,state) if all(v['domain']=='continuous' for v in m['variables']) else certify_discrete(m,state)
        checked.append({**r,'solve':state,'independent_certificate':cert,'audit_status':'numerically_verified_transcription' if cert['verified'] else 'numeric_audit_incomplete'})
    report=dict(schema='input-bound-reference-audit-v1',records=checked,blocked=blocked,prepared=len(prepared),numerically_verified=sum(r['independent_certificate']['verified'] for r in checked),
                native_reference_values_used=False,expert_semantic_certification=False,actual_model_api_calls=0)
    write_json(ROOT/'data/evaluation/reference_models_v1.json',report)
    print(json.dumps({k:report[k] for k in ('prepared','numerically_verified','blocked','actual_model_api_calls')}))


if __name__=='__main__':main()
