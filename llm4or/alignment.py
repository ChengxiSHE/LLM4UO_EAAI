"""Post-inference, explicitly reviewed bijective unit conversion, never repair."""
from copy import deepcopy

from .schema import digest, model, number


def align_units(candidate,reference,review):
    candidate,reference=model(candidate),model(reference)
    if (review.get('status')!='semantic_mapping_reviewed'
            or review.get('candidate_hash')!=digest(candidate)
            or review.get('reference_hash')!=digest(reference)
            or not review.get('rationale')):
        raise ValueError('reviewed mapping provenance required')
    mapping=review['variable_mapping'];scales=review['reference_quantity_per_candidate_unit']
    source={v['id']:v for v in candidate['variables']};target={v['id']:v for v in reference['variables']}
    if (set(mapping)!=set(source) or set(mapping.values())!=set(target)
            or len(mapping)!=len(target) or set(scales)!=set(source)):
        raise ValueError('mapping must be a complete bijection')
    for old,new in mapping.items():
        if number(scales[old])<=0:raise ValueError('positive unit scale required')
        if source[old]['domain']!=target[new]['domain']:raise ValueError('domain cannot be changed')
    objective_scale=number(review['reference_objective_unit_per_candidate_unit'])
    if objective_scale<=0:raise ValueError('positive objective scale required')
    result=deepcopy(candidate)
    for v in result['variables']:
        old=v['id'];r=target[mapping[old]]
        for side in ('lower','upper'):
            if v[side] is not None:v[side]*=scales[old]
        v.update(id=r['id'],meaning=r['meaning'],unit=r['unit'])
    for row in result['constraints']:
        row['coefficients']={mapping[k]:c/scales[k] for k,c in row['coefficients'].items()}
    obj=result['objective']
    obj['coefficients']={mapping[k]:c/scales[k]*objective_scale for k,c in obj['coefficients'].items()}
    obj['offset']*=objective_scale;obj['unit']=reference['objective']['unit']
    return model(result)
