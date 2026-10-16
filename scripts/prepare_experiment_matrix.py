"""Freeze an offline experiment proposal; never authorizes or starts model calls."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from llm4or.pipeline import write_json
from llm4or.schema import digest


def main():
    refs=json.loads((ROOT/'data/manifests/reference_readiness_summary.json').read_text())
    families=json.loads((ROOT/'data/manifests/benchmark_family_isolation.json').read_text())
    rows=[
      dict(id='Base',description='One direct structured formulation.',max_requests_per_problem=1,implementation='offline_milp_initial_available'),
      dict(id='SolverRepair',description='Initial formulation and up to two solver-feedback repairs.',max_requests_per_problem=3,implementation='one_repair_offline_two_repair_runner_pending'),
      dict(id='A',description='Frozen teacher, executable differences and scoped repair gate.',max_requests_per_problem=4,implementation='fixed_offline_milp_pipeline_available'),
      dict(id='B',description='Workflow evolution using terminal development feedback and text diagnosis; same atomic tool availability.',max_requests_per_problem=4,implementation='DSL_proposer_selection_inheritance_pending'),
      dict(id='SimpleAB',description='Generic workflow search with A operations and the same evidence/tools; no paired contrastive teaching.',max_requests_per_problem=6,implementation='DSL_proposer_selection_inheritance_pending'),
      dict(id='Full',description='Evidence-linked paired repair outcomes, scoped repairs and fresh-family update acceptance.',max_requests_per_problem=6,implementation='teacher_and_gates_available_full_evolution_pending')]
    n=families['source_records'];seeds=[17,31,47]
    requests=n*len(seeds)*sum(r['max_requests_per_problem'] for r in rows)
    ready=refs['counts'].get('numeric_transcription_and_native_label_agree',0)
    proposal=dict(schema='formal-experiment-proposal-v1',status='offline_proposal_not_authorized_not_ready',api_enabled=False,authorized_requests=0,
                  source_records=n,full_reporting_cohort_sha256=families['full_reporting_cohort_sha256'],
                  independent_test_denominator=None,methods=rows,seeds=seeds,
                  common_information='description_parameters_v1; ComplexOR parameter-metadata-v1; no scaffold or gold',
                  logical_token_caps_per_problem=[16384,32768,65536],max_completion_tokens_per_request=8192,
                  token_cap_status='proposal_only_needs_complete_provider_accounting_and_pre_call_reservation',
                  request_ceiling_one_budget_setting_no_shared_prefix_savings=requests,
                  completion_token_ceiling_one_budget_setting=requests*8192,
                  interpretation='Arithmetic upper bound, not expected usage, a currency quote, or authorization. Each additional budget setting may require another complete matrix unless valid prefix reuse is specified.',
                  development_evolution_budget='Separate proposal after verified fresh family inventory and DSL implementation; not borrowed from inference caps.',
                  reference_ready_count=ready,reference_not_ready_count=n-ready,
                  known_development_overlap_records=families['quarantined_benchmark_records'],certified_fresh_families=0,
                  reporting=dict(full_cohort=True,known_development_overlap_separate=True,unknown_unsupported_timeout_retained=True,
                                 objective_status_proxy_separate_from_formulation=True,paired_same_initial_prefix=True,charge_shared_prefix_to_each_logical_method=True,
                                 independence_unit='reviewed_semantic_family_not_model_call_or_lexical_component'),
                  startup_blockers=['All non-ambiguous reference/input bindings need an audited grading policy; only 12 numeric transcriptions currently agree.',
                                    'Semantic family review and frozen propose/select/gate/test roles are incomplete; lexical components are not iid proof.',
                                    'B, SimpleAB and Full still require executable DSL proposal, selection and inheritance.',
                                    'Unsupported nonlinear/conic coverage and every method adapter require an explicit full-cohort protocol.',
                                    'New provider/token accounting, unique ledger and explicit paid-scope authorization are required.'])
    write_json(ROOT/'experiments/formal_matrix_v1.json',proposal)
    print(json.dumps({k:proposal[k] for k in ('source_records','reference_ready_count','reference_not_ready_count','known_development_overlap_records','request_ceiling_one_budget_setting_no_shared_prefix_savings','authorized_requests')}))


if __name__=='__main__':main()
