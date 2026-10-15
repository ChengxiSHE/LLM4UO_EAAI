"""Bounded two-stage program selection with precommitted, disjoint gate batches.

The controller sees development Boolean proxy scores only. The proposer sees
aggregates, never labels, source code, problems, answers or test trajectories.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
from .schema import Invalid, digest
from .milp_schema import loads
from .pipeline import write_json
from .workflow import apply_patch, compile_program, proposal_payload
from .gates import paired_evolution_gate
from .run_interruption import RunInterrupted


def diagnostic_bundle(method, pairs):
    eligible=[pair for pair in pairs if all(v.get('available',True) for v in pair)]
    flat=[v for pair in eligible for v in pair]
    base={'terminal':dict(Counter('published_proxy_match' if v['score'] else 'no_certified_proxy_match' for v in flat)),
          'errors':dict(Counter(e['phase'] for v in flat for e in v['run'].get('errors',[]))),
          'available_pairs':len(eligible),'unavailable_pairs':len(pairs)-len(eligible),
          'description':'Scores are published-label proxy outcomes, not semantic truth. Infrastructure-unavailable pairs are reported and excluded.'}
    if method!='B':
        base['evidence_features']=dict(Counter(k for v in flat for k,x in v['run'].get('features',{}).items() if x))
    if method=='Full':
        grouped={}
        for old,new in eligible:
            # Features from before the first changed node, not post-outcome
            # features. Initial shared prefix is common to both trajectories.
            trace=old['run'].get('trace',[])
            features=trace[0].get('features',{}) if trace else {}
            key=digest(features)
            g=grouped.setdefault(key,{'pre_action_features':features,'n':0,'new_only_match':0,'old_only_match':0,'both_match':0,'neither_match':0})
            g['n']+=1
            category='both_match' if old['score'] and new['score'] else 'new_only_match' if new['score'] else 'old_only_match' if old['score'] else 'neither_match'
            g[category]+=1
        base['paired_action_outcomes']=list(grouped.values())
        base['pair_definition']='Incumbent versus one fixed legal local deletion/insertion, complete reruns with cached identical initial prefix; both logical costs charged.'
    return base


def contrast_program(program):
    if program['nodes']: return apply_patch(program,{'kind':'delete','index':0,'value':None})
    return apply_patch(program,{'kind':'insert','index':0,'value':{'op':'solver_repair','guard':'always','scope':'whole_model'}})


class Evolution:
    def __init__(self, directory, split, generations, streams, *, execute_scored, propose, parallel_map=None):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.split=split;self.generations=generations;self.streams=streams
        self.execute_scored=execute_scored;self.propose=propose
        self.parallel_map=parallel_map or (lambda function,items:[function(x) for x in items])
        self.families={f['id']:f for f in split['families']}
        used=[]
        for group in split['schedules']['gate'][:generations]:
            if not group or any(self.families[f]['role']!='update_gate' for f in group):raise Invalid('gate_role')
            used.extend(group)
        if len(set(used))!=len(used):raise Invalid('gate_family_reuse')
        for stage,role in [('build','development_propose'),('select','development_select')]:
            allowed={x for f in split['families'] if f['role']==role for x in f['members']}
            if not set(split['schedules'][stage])<=allowed:raise Invalid('development_role_overlap')

    def frozen_write(self,path,value):
        path=self.directory/path
        if path.exists():
            if json.loads(path.read_text())!=value:raise Invalid('evolution_frozen_state_changed:'+path.name)
        else:write_json(path,value)

    def run(self, initial):
        current=deepcopy(initial)
        identity={'split_hash':digest(self.split),'generations':self.generations,'streams':self.streams,'initial':current}
        self.frozen_write(Path('identity.json'),identity)
        for gen in range(1,self.generations+1):
            chosen={}
            # ALL method/replicate candidates are frozen before ANY gate
            # outcome for this generation can be opened.
            for stream in self.streams:
                method=stream.split(':')[0];inc=current[stream];alt=contrast_program(inc)
                build_tasks=[(pid,label,p) for pid in self.split['schedules']['build'] for label,p in [('inc',inc),('contrast',alt)]]
                build_values=self.parallel_map(lambda x:self.execute_scored('build',stream,gen,x[1],x[0],x[2]),build_tasks)
                pairs=[tuple(build_values[i:i+2]) for i in range(0,len(build_values),2)]
                diagnostics=diagnostic_bundle(method,pairs)
                packet=proposal_payload(inc,diagnostics,method,gen)
                candidates=[];rejected=[]
                try:
                    raw=loads(self.propose(stream,gen,packet))
                    if set(raw)!={'patches'} or not isinstance(raw['patches'],list) or len(raw['patches'])>2:raise Invalid('proposal_contract')
                    for patch in raw['patches']:
                        try:
                            candidate=apply_patch(inc,patch)
                            if digest(candidate) in {digest(x['program']) for x in candidates}:raise Invalid('duplicate_candidate')
                            candidates.append({'program':candidate,'patch':patch})
                        except (ValueError,TypeError,KeyError) as exc:rejected.append(type(exc).__name__)
                except RunInterrupted:
                    raise
                except (ValueError,RuntimeError,TypeError,KeyError) as exc:rejected.append(type(exc).__name__)
                labels=[('inc',inc)]+[(str(i),v['program']) for i,v in enumerate(candidates)]
                select_tasks=[(pid,label,program) for pid in self.split['schedules']['select'] for label,program in labels]
                select_values=self.parallel_map(lambda x:self.execute_scored('select',stream,gen,x[1],x[0],x[2]),select_tasks)
                by_pid={};width=len(labels)
                for i,pid in enumerate(self.split['schedules']['select']):
                    by_pid[pid]={label:select_values[i*width+j] for j,(label,_) in enumerate(labels)}
                eligible_pids=[pid for pid,values in by_pid.items() if all(v.get('available',True) for v in values.values())]
                scores=[]
                for label,program in labels:
                    values=[by_pid[pid][label] for pid in eligible_pids]
                    scores.append({'label':label,'program_hash':digest(program),'matches':sum(v['score'] for v in values),
                                   'available':len(values),'unavailable':len(by_pid)-len(values),
                                   'nodes':len(program['nodes']),'tokens':sum(v['run'].get('usage',{}).get('logical_tokens',0) for v in values)})
                winner=min(scores,key=lambda x:(-x['matches'],x['nodes'],x['tokens'],x['program_hash'])) if eligible_pids else scores[0]
                candidate=inc if winner['label']=='inc' else candidates[int(winner['label'])]['program']
                frozen={'generation':gen,'stream':stream,'incumbent':inc,'candidate':candidate,'candidate_hash':digest(candidate),
                        'diagnostics':diagnostics,'candidates':candidates,'rejected':rejected,'selection':scores,
                        'gate_families':self.split['schedules']['gate'][gen-1],
                        'gate_metric':'published_proxy_match; unresolved counts as no match',
                        'alpha':.05/len(self.streams)/(gen*(gen+1))}
                self.frozen_write(Path(f'g{gen}_{stream.replace(":","_")}_frozen.json'),frozen)
                chosen[stream]=frozen
            self.frozen_write(Path(f'g{gen}_all_candidates_committed.json'),{k:v['candidate_hash'] for k,v in chosen.items()})
            for stream,frozen in chosen.items():
                inc,candidate=frozen['incumbent'],frozen['candidate'];outcomes=[]
                if digest(inc)!=digest(candidate):
                    gate_tasks=[(self.families[fid]['representative'],label,program) for fid in frozen['gate_families'] for label,program in [('inc',inc),('candidate',candidate)]]
                    gate_values=self.parallel_map(lambda x:self.execute_scored('gate',stream,gen,x[1],x[0],x[2]),gate_tasks)
                    for i in range(0,len(gate_values),2):
                        old,new=gate_values[i:i+2]
                        if old.get('available',True) and new.get('available',True):outcomes.append((old['score'],new['score']))
                    if len(outcomes)!=len(frozen['gate_families']):
                        result={'accept':False,'reason':'infrastructure_incomplete_gate','pvalue':None,'threshold':frozen['alpha'],
                                'available_pairs':len(outcomes),'planned_pairs':len(frozen['gate_families'])}
                    else:result=paired_evolution_gate(outcomes,gen,delta=.05/len(self.streams))
                else:result={'accept':False,'reason':'no_candidate_selected','pvalue':1.0,'threshold':frozen['alpha']}
                result.update(candidate_hash=digest(candidate),incumbent_hash=digest(inc),families=frozen['gate_families'],
                              outcomes=outcomes,independence_certified=False,
                              statistical_scope='empirical update; nominal error control conditional on reliable proxy labels and independent semantic families')
                # JSON normalizes tuples so restart comparisons are stable.
                result=json.loads(json.dumps(result))
                self.frozen_write(Path(f'g{gen}_{stream.replace(":","_")}_gate.json'),result)
                if result['accept']:current[stream]=candidate
            self.frozen_write(Path(f'g{gen}_inherited.json'),current)
        self.frozen_write(Path('final_programs.json'),current)
        return current
