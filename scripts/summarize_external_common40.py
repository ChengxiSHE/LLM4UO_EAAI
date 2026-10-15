#!/usr/bin/env python3
"""Bound the completed fixed-40 comparison; no generation, solving or rescoring."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from llm4or.pipeline import write_json
from llm4or.schema import digest
from scripts.audit_external_comparison_cohorts import sha,read,PUBLIC_MANIFEST

REPORTS={
    'base':'results/base_fixed_common40.json', 'bind':'results/bind_fixed_common40.json',
    'coe':'results/coe_fixed_common40.json', 'skillopt':'results/skillopt_text2opt_reproduction.json',
    'alphaopt':'results/alphaopt_common_reproduction.json',
    'base_cost':'results/base_fixed_common40_cost.json','bind_cost':'results/bind_fixed_common40_cost.json',
    'coe_cost':'results/coe_fixed_common40_cost.json',
}
PLANS={
    'base':'experiments/base_common40_completion_plan.json',
    'bind':'experiments/bind_common40_completion_plan.json',
    'coe':'experiments/coe_common40_completion_recovery_plan.json',
    'skillopt':'experiments/skillopt_text2opt_test_recovery_plan.json',
    'alphaopt':'experiments/alphaopt_common_reproduction_plan.json',
}


def checked_row(name,correct,runs,unavailable,*,repeats=1,endpoint='benchmark status/objective',information='public problem only',families=None):
    if (any(type(v) is not int for v in (correct,runs,unavailable,repeats)) or repeats<1
            or runs!=40*repeats or not 0<=correct<=runs-unavailable or not 0<=unavailable<=runs):
        raise ValueError('comparison_denominator_or_score')
    if families is not None:
        if (set(families)!={'rcpsp','vrptw'} or any(v['runs']!=20*repeats for v in families.values())
                or sum(v['correct'] for v in families.values())!=correct):
            raise ValueError('comparison_family_denominator')
    return {'method':name,'correct':correct,'planned_runs':runs,'distinct_problems':40,'repeats':repeats,
            'accuracy_all_planned':correct/runs,'infrastructure_unavailable':unavailable,
            'endpoint':endpoint,'information':information,'families':families}


def summarize(root=ROOT):
    root=root.resolve();sources={name:read(root/path) for name,path in REPORTS.items()}
    plans={name:read(root/path) for name,path in PLANS.items()}
    manifest=read(root/PUBLIC_MANIFEST);target={r['id']:r for r in manifest['roles']['test']};manifest_hash=sha(root/PUBLIC_MANIFEST)
    if len(target)!=40 or Counter(r['family'] for r in target.values())!={'rcpsp':20,'vrptw':20}:
        raise ValueError('comparison_target_changed')
    for name,plan in plans.items():
        auth=read(root/PLANS[name].replace('_plan.json','_authorization.json'))
        if auth.get('plan_sha256')!=digest(plan) or auth.get('further_api_calls_authorized') is not False:
            raise ValueError('comparison_run_not_closed:'+name)
        if (plan['model'],plan['reasoning_effort'])!=('gpt-6-luna','high'):
            raise ValueError('comparison_backbone_changed')
        if name in ('base','skillopt','alphaopt') and sources[name]['plan_sha256']!=digest(plan):
            raise ValueError('comparison_report_plan:'+name)
        if name in ('skillopt','alphaopt') and (plan['public_manifest_sha256']!=manifest_hash
                or any(plan['public_inputs'].get(i)!=target[i]['public_input_sha256'] for i in target)):
            raise ValueError('comparison_public_binding:'+name)
    for name in ('base','bind','coe'):
        if sources[name]['target_manifest_sha256']!=manifest_hash:
            raise ValueError('comparison_report_cohort:'+name)
    for name in ('bind','coe'):
        if digest(plans[name]) not in {s['plan_sha256'] for s in sources[name]['source_runs']}:
            raise ValueError('comparison_completed_source_missing:'+name)
    for name in ('base','bind','coe'):
        cost=sources[name+'_cost']
        if cost['source_result_sha256']!=sha(root/REPORTS[name]):raise ValueError('comparison_cost_result_binding:'+name)
    base,bind,coe,skill,alpha=[sources[k] for k in ('base','bind','coe','skillopt','alphaopt')]
    if ({r['problem_id'] for r in base['cells']}!=set(target) or len(base['cells'])!=40 or set(bind['cells'])!=set(target)
            or set(coe['cells'])!={'coec_'+s+'_'+i.removeprefix('text2opt_') for s in ('paper','current') for i in target}):
        raise ValueError('comparison_distinct_identity_set')
    if (sum(c['correct'] for c in base['cells'])!=base['counts']['correct']
            or sum(c['infrastructure_unavailable'] for c in base['cells'])!=base['counts']['infrastructure_unavailable']):
        raise ValueError('comparison_base_cell_counts')
    if sources['base_cost']['included_problems']!=40 or sources['coe_cost']['included_identities_per_snapshot']!=40 or sources['bind_cost']['included_problems']!=40:
        raise ValueError('comparison_cost_subset_incomplete')
    rows=[]
    rows.append(checked_row('Base',base['counts']['correct'],40,base['counts']['infrastructure_unavailable'],
                            families={f:{'correct':v['correct'],'runs':v['planned']} for f,v in base['by_family'].items()}))
    for field,label,info in [('round1_correct','BIND first round','public structured instance; no answer-feedback round'),
                            ('final_correct','BIND official final','official answer-bearing repair feedback')]:
        rows.append(checked_row(label,bind['counts'][field],40,40-bind['counts']['evaluated'],information=info,
                                families={f:{'correct':v[field],'runs':v['planned']} for f,v in bind['by_family'].items()}))
    for snapshot in ('paper','current'):
        counts=coe['by_snapshot'][snapshot]
        for endpoint,label in [('author_exact','strict author scalar'),('scalar_tolerance','scalar tolerance; no dictionary projection')]:
            rows.append(checked_row('CoE '+snapshot+' / '+endpoint,counts[endpoint],40,counts['infrastructure_unavailable'],endpoint=label,
                                    families={f:{'correct':v[snapshot][endpoint],'runs':v[snapshot]['planned']} for f,v in coe['by_family'].items()}))
    for method in ('empty_skill','best_skill'):
        value=skill['methods_all_selected'][method]
        rows.append(checked_row('SkillOpt '+method,value['correct'],value['planned_records'],value['infrastructure_unavailable'],
                                families={f:{'correct':v['correct'],'runs':v['n']} for f,v in value['categories'].items()}))
    if alpha['distinct_problem_records']!=40 or alpha['repeats']!=3 or len(plans['alphaopt']['replicates'])!=3:
        raise ValueError('comparison_alpha_repeats')
    for method in ('no_library','released_library','no_library_static_v9','released_library_static_v9','no_library_conservative_v9','released_library_conservative_v9'):
        value=alpha['methods_all_selected_runs'][method]
        rows.append(checked_row('AlphaOPT '+method,value['correct'],value['runs'],value['infrastructure_unavailable'],repeats=3,
                                families={f:{'correct':v[method]['correct'],'runs':v[method]['runs']} for f,v in alpha['per_family'].items()}))
    report={'schema':'external-fixed40-summary-v1','role':'retrospective_comparison_without_new_scoring',
            'target_manifest':PUBLIC_MANIFEST,'target_manifest_sha256':manifest_hash,'distinct_problem_records':40,
            'families':{'rcpsp':20,'vrptw':20},'model':'gpt-6-luna','reasoning_effort':'high','rows':rows,
            'artifact_hashes':{path:sha(root/path) for path in list(REPORTS.values())+list(PLANS.values())},'script_sha256':sha(Path(__file__)),
            'cost_groups':{'Base_40':sources['base_cost']['totals'],
                           'BIND_first_round_40':sources['bind_cost']['first_round'],
                           'BIND_all_rounds_40_includes_first_round':sources['bind_cost']['all_rounds'],
                           'CoE_paper_40':sources['coe_cost']['by_snapshot']['paper'],
                           'CoE_current_40':sources['coe_cost']['by_snapshot']['current'],
                           'AlphaOPT_joint_two_conditions_three_repeats':{k:alpha['ledger'][k] for k in ['physical_attempts','retry_attempts','physical_reserved_or_reported_tokens']},
                           'SkillOpt_cost_boundary':'Training/selection/test and copied/imported ledgers require separate attribution; do not label current_run_ledger as per-row test cost.'},
            'coe_execution_limits':{snapshot:{k:coe['by_snapshot'][snapshot][k] for k in
                ('planned','complete','method_failure','infrastructure_unavailable','adapter_supported','adapter_unsupported')}
                for snapshot in ('paper','current')},
            'baseline_policy':'Preserve all fixed results and official method settings. No score-driven tuning, optional variants or favorable reruns; subsequent optimization concerns our method.',
            'interpretation_limits':[
                'Same 40 identities and backbone do not make input representation, official rounds, solver/adapter limits or information access identical.',
                'BIND final uses answer-bearing repair; do not call it answer-blind inference or merge it with first round.',
                'CoE strict scalar and scalar-tolerance contracts exclude dictionary-field projection; these columns are not full semantic formulation judgments.',
                'All method and safe-adapter failures stay in planned denominators. Infrastructure unavailability is reported separately.',
                'AlphaOPT has 40 problems repeated three times, not 120 independent problems. No new significance tests or rankings are selected here.',
                'Static V9 composition is an author-built compiler wrapper, not evidence of automatic harness evolution.',
                'SkillOpt and AlphaOPT adaptations retain substantial transport/execution limitations; do not attribute every failure to native method reasoning.',
                'No OptiTrust score is available from a verified official reproduction. No paper score fills that cell.',
                'These exposed two-family results do not replace fresh-source confirmation or prove top-conference readiness.',
                'Cost groups overlap (BIND final includes round one; AlphaOPT cost covers both conditions). Never sum rows as disjoint costs.'
            ],'new_model_calls':0,'new_solver_calls':0}
    write_json(root/'results/external_fixed_common40_summary.json',report)
    text=['# 固定 40 题外部比较','', '回顾性队列：20 道 RCPSP、20 道 VRPTW；共同模型为 gpt-6-luna（high）。仅汇总本地完成结果，不重跑、不重新评分。','',
          '| 方法 | 正确 / 全部计划运行 | 正确比例 | 不同题目 × 重复 | 基础设施不可用 | 评价端点 |',
          '|---|---:|---:|---:|---:|---|']
    for r in rows:
        text.append(f"| {r['method']} | {r['correct']}/{r['planned_runs']} | {r['accuracy_all_planned']:.2%} | 40 × {r['repeats']} | {r['infrastructure_unavailable']} | {r['endpoint']} |")
    text+=['','BIND official final 使用参考答案驱动的修复反馈；各方法的输入形式、轮数、资源和安全适配限制并不完全相同，因此该表不是无条件的统一排名。AlphaOPT 的 120 次运行只来自 40 道题。','',
           'CoE 的 scalar tolerance 不包含字典字段投影；所有方法失败和适配失败均保留在分母。静态 V9 组合不等于自动进化结果。OptiTrust 暂无已核实的官方复现结果，不能填入论文分数。','',
           f"CoE paper/current 分别有 {coe['by_snapshot']['paper']['adapter_unsupported']}/{coe['by_snapshot']['current']['adapter_unsupported']} 个已完成输出超出固定安全适配器的支持范围。这些限制是低分的重要解释边界，不能把适配失败当作原生 CoE 的建模错误。",'',
           '上述基线结果固定保留；不因分数低而调提示词、增加轮数、搜索配置或择优重跑。论文方法本身规定的训练与修复流程保留，后续改进集中于我们的方法。','',
           '逐来源哈希、家族分项、费用边界和完整解释限制见 [`external_fixed_common40_summary.json`](../results/external_fixed_common40_summary.json)。费用为账本 token，不是服务商发票；BIND 两个费用组重叠，AlphaOPT 费用为两种条件及三次重复的合计。','']
    (root/'docs/EXTERNAL_FIXED_COMMON40_RESULTS.md').write_text('\n'.join(text))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-readiness',action='store_true');args=parser.parse_args()
    if args.check_readiness:
        print(json.dumps({'missing':[p for p in REPORTS.values() if not (ROOT/p).exists()],'new_model_calls':0,'new_solver_calls':0}))
    else:
        value=summarize();print(json.dumps({'distinct_problems':40,'rows':len(value['rows']),'new_model_calls':0,'new_solver_calls':0}))
