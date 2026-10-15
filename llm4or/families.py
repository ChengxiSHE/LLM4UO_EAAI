"""Conservative public-text duplicate candidates, not a semantic equivalence oracle."""
import hashlib
import json
import re

ANCHORS = {
    'wilson_crop': ('wilson creek farm',),
    'southfork_feed': ('southfork feed',),
    'western_pulp': ('western pulp',),
    'birdie_fertilizer': ('birdie valley',),
    'euing_gas': ('euing gas',),
    'candy_counter': ('chocolate maker', 'candy counter'),
    'kalo_fertilizer': ('kalo fertilizer',),
    'bullneck_diet': ('bullneck',),
    'kilroy_fire': ('kilroy', 'fire station'),
    'gandhi_setup': ('gandhi cloth',),
    'glueco_setup': ('glueco',),
    'comp_max': ('comp-max',),
    'dorian_production': ('dorian auto', 'manufacturing'),
    'warehouse_four_cities': ('warehouses', 'new york', 'atlanta'),
}


def normalize(text, mask_numbers=False):
    text = re.sub(r'\s+', ' ', text.casefold()).strip()
    if mask_numbers:
        text = re.sub(r'\b\d+(?:[.,]\d+)*%?\b', 'NUMBER', text)
    return text


def public_inventory(root, manifest):
    records = []
    for source in manifest['records']:
        path = root/source['local_path']
        if path.suffix not in {'.json', '.jsonl'}: continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('raw source hash mismatch')
        if path.suffix == '.jsonl':
            rows = [next(iter(json.loads(line).values())) for line in raw.splitlines() if line.strip()]
            field = 'document'
        else:
            rows = json.loads(raw)
            field = 'description' if 'description' in rows[0] else 'question'
        prefix = hashlib.sha256(source['local_path'].encode()).hexdigest()[:10]
        for index, row in enumerate(rows):
            # Project immediately. No gold, code, formulations, or evaluation
            # statistics leave this loader; no external code is executed.
            text = row[field]
            if not isinstance(text, str) or not text.strip(): raise ValueError('empty public text')
            records.append({'id':f'p_{prefix}_{index:04}', 'text':text,
                            'source_path':source['local_path'], 'source_row_zero_based':index,
                            'source_sha256':source['sha256'],
                            'source_type_tag':row.get('type'),
                            'public_text_hash':hashlib.sha256(text.encode()).hexdigest()})
    return records


def group_candidates(records, threshold=0.86):
    """Union conservative candidate edges; component IDs never imply proven families."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    if not 0 < threshold <= 1:
        raise ValueError('similarity threshold must be in (0, 1]')
    if len({r['id'] for r in records}) != len(records):
        raise ValueError('duplicate public record ID')
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i

    edges = []
    edge_keys = set()
    def link(i,j,kind,score=None):
        key = (min(i,j),max(i,j),kind)
        if key in edge_keys: return
        edge_keys.add(key)
        parent[find(j)] = find(i)
        edges.append({'left':records[i]['id'],'right':records[j]['id'],'reason':kind,'similarity':score})

    for mask in (False,True):
        seen = {}
        for i,r in enumerate(records):
            key=normalize(r['text'],mask)
            if key in seen: link(seen[key],i,'number_masked_exact' if mask else 'normalized_exact',1.0)
            else: seen[key]=i
    for name,tokens in ANCHORS.items():
        members=[i for i,r in enumerate(records) if all(t in r['text'].casefold() for t in tokens)]
        for i in members[1:]: link(members[0],i,'reviewed_named_problem:'+name)
    # Text-only lexical candidates. A high score is not proof of same family;
    # low similarity cannot establish independence. No embeddings/API calls.
    if len(records)>1:
        vectorizer=TfidfVectorizer(analyzer='word',ngram_range=(1,2),sublinear_tf=True,max_features=120000)
        texts = [normalize(r['text'],True) for r in records]
        if any(vectorizer.build_analyzer()(t) for t in texts):
            matrix=vectorizer.fit_transform(texts)
            similarities=(matrix@matrix.T).tocoo()
            for i,j,score in zip(similarities.row,similarities.col,similarities.data):
                if i<j and score>=threshold: link(int(i),int(j),'lexical_candidate',round(float(score),6))
    groups={}
    for i,r in enumerate(records): groups.setdefault(find(i),[]).append(r['id'])
    components=[]
    membership={}
    for members in groups.values():
        members=sorted(members)
        gid='family_candidate_'+hashlib.sha256('|'.join(members).encode()).hexdigest()[:12]
        components.append({'id':gid,'members':members,'status':'conservative_candidate_not_verified_semantic_family'})
        membership.update({m:gid for m in members})
    return sorted(components,key=lambda g:g['id']),membership,edges
