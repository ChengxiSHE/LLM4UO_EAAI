"""Persistently reserve reviewed, fresh families BEFORE observing gate outcomes."""
import json
import re
from pathlib import Path
import sqlite3
from .schema import Invalid,digest
from .gates import paired_evolution_gate


class FreshFamilyGate:
    def __init__(self,path,manifest):
        if manifest.get('schema')!='reviewed-family-split-v1' or manifest.get('review_status')!='reviewed':
            raise Invalid('semantic_family_review_required')
        self.families={}; all_ids=set()
        for family in manifest.get('families',[]):
            fid=family['id']; members=family['members']
            if fid in self.families or not members or len(set(members))!=len(members) or all_ids&set(members):raise Invalid('family_overlap')
            if family['role'] not in {'development_propose','development_select','update_gate','locked_test','quarantine'}:raise Invalid('family_role')
            if not family.get('review_note'):raise Invalid('missing_family_review')
            self.families[fid]=family;all_ids.update(members)
        if not self.families:raise Invalid('empty_family_manifest')
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.manifest_hash=digest(manifest)
        with sqlite3.connect(self.path) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, hash TEXT); CREATE TABLE IF NOT EXISTS batches (generation INTEGER PRIMARY KEY, incumbent TEXT, candidate TEXT, families TEXT, result TEXT); CREATE TABLE IF NOT EXISTS used (family TEXT PRIMARY KEY, generation INTEGER);')
            prior=db.execute('SELECT hash FROM metadata WHERE id=1').fetchone()
            if prior and prior[0]!=self.manifest_hash:raise Invalid('split_changed_cannot_reset_freshness')
            db.execute('INSERT OR IGNORE INTO metadata VALUES (1,?)',(self.manifest_hash,))

    def reserve(self,generation,incumbent_hash,candidate_hash,families):
        if type(generation) is not int or generation<1 or not families or len(set(families))!=len(families):raise Invalid('invalid_gate_batch')
        if incumbent_hash==candidate_hash:raise Invalid('unchanged_candidate')
        if any(not isinstance(h,str) or not re.fullmatch('[a-f0-9]{64}',h) for h in (incumbent_hash,candidate_hash)):raise Invalid('program_hash_required')
        if any(f not in self.families or self.families[f]['role']!='update_gate' for f in families):raise Invalid('non_gate_or_unknown_family')
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM batches WHERE generation=?',(generation,)).fetchone():raise Invalid('generation_already_reserved')
            if db.execute('SELECT count(*) FROM batches').fetchone()[0]!=generation-1:raise Invalid('generation_sequence')
            if generation>1:
                previous=db.execute('SELECT incumbent,candidate,result FROM batches WHERE generation=?',(generation-1,)).fetchone()
                if previous[2] is None:raise Invalid('previous_gate_not_finished')
                expected=previous[1] if json.loads(previous[2])['accept'] else previous[0]
                if incumbent_hash!=expected:raise Invalid('incumbent_not_inherited')
            try:
                for f in families:db.execute('INSERT INTO used VALUES (?,?)',(f,generation))
            except sqlite3.IntegrityError as e:raise Invalid('family_not_fresh') from e
            db.execute('INSERT INTO batches VALUES (?,?,?,?,NULL)',(generation,incumbent_hash,candidate_hash,json.dumps(families)))
        return dict(generation=generation,incumbent_hash=incumbent_hash,candidate_hash=candidate_hash,families=families,split_hash=self.manifest_hash)

    def evaluate(self,generation,candidate_hash,outcomes):
        with sqlite3.connect(self.path) as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT candidate,families,result FROM batches WHERE generation=?',(generation,)).fetchone()
            if row is None or row[0]!=candidate_hash:raise Invalid('candidate_not_frozen_before_gate')
            if row[2] is not None:raise Invalid('gate_already_consumed')
            families=json.loads(row[1])
            if set(outcomes)!=set(families):raise Invalid('gate_denominator_changed')
            # Exactly one prespecified binary pair per reviewed family.
            result=paired_evolution_gate([outcomes[f] for f in families],generation)
            result.update(freshness_and_candidate_freeze_enforced=True,split_hash=self.manifest_hash,
                          independence_scope='depends_on_external_semantic_review_and_sampling_not_lexical_components')
            db.execute('UPDATE batches SET result=? WHERE generation=?',(json.dumps(result),generation))
        return result
