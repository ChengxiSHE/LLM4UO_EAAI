"""Conservative, label-blind semantic template anchors for split isolation.

Each rule groups a broad problem class rather than treating parameter values,
business names or paraphrases as independent families. Multiple anchors merge
their complete groups; overmerging costs power but does not create leakage.
Unrecognized semantics are NOT certified fresh by this rule set.
"""
import re
from .schema import digest

TEMPLATES={
    'diet_nutrient_cost':(r'\b(?:nutrient|nutrition|vitamin|protein|calories)\w*\b',r'\b(?:cost|diet|feed|food)\w*\b'),
    'transport_supply_demand':(r'\b(?:transport|ship|distribut|deliver)\w*\b',r'\b(?:warehouse|factory|factories|plant|supply|demand)\b'),
    'resource_constrained_product_mix':(r'\b(?:produc|manufactur|crop|planting)\w*\b',r'\b(?:profit|maximiz)\w*\b',r'\b(?:hours?|labor|labour|capacity|resources?|acres?|land)\b'),
    'knapsack':(r'\bknapsack\b|\bbackpack\b',),
    'bin_packing':(r'\bbin[- ]packing\b|\bbins?\b',r'\bpack\w*\b|\bcapacity\b'),
    'cutting_stock':(r'\bcutting[- ]stock\b|\bcut\w*\b',r'\brolls?\b|\bpatterns?\b|\btrim\b'),
    'facility_location':(r'\bfacilit\w*\b|\bwarehouses?\b',r'\blocati\w*\b|\bopen\w*\b|\bestablish\w*\b'),
    'set_cover':(r'\bset[- ]cover\w*\b|\bcovering problem\b',),
    'graph_coloring':(r'\bcolor\w*\b|\bcolour\w*\b',r'\bgraph\b|\bvertices\b|\badjacent\b'),
    'shortest_path':(r'\bshortest[- ]path\b|\bshortest route\b',),
    'max_flow':(r'\bmax(?:imum)?[- ]flow\b|\bmaximum flow\b',),
    'minimum_cost_flow':(r'\bmin(?:imum)?[- ]cost[- ]flow\b|\bminimum cost flow\b',),
    'traveling_salesperson':(r'\btravel(?:l)?ing sales\w*\b|\bvisit each city\b|\bvisits? (?:each|every) (?:node|city) (?:exactly )?once\b',),
    'vehicle_routing':(r'\bvehicle routing\b|\brout\w*\b',r'\bvehicles?\b|\btrucks?\b|\bdepot\b'),
    'assignment':(r'\bassign\w*\b',r'\bexactly one\b|\bone[- ]to[- ]one\b|\bone (?:worker|job|machine|task)\b'),
    'job_shop':(r'\bjob[- ]shop\b|\bflow[- ]shop\b',),
    'precedence_scheduling':(r'\bprecedence\b|\bpredecessor\w*\b',r'\bschedul\w*\b|\bproject\b'),
    'workforce_shift_cover':(r'\bshifts?\b',r'\bstaff\b|\bnurses?\b|\bemployees?\b|\bworkers?\b'),
    'portfolio':(r'\bportfolio\b|\basset allocation\b',),
    'blending':(r'\bblend\w*\b|\bmixture\b',r'\bquality\b|\bpercent\w*\b|\bcomposition\b|\bingredients?\b'),
    'inventory_lot_sizing':(r'\binventor\w*\b|\blot[- ]siz\w*\b',r'\bperiod\w*\b|\bmonths?\b|\bweeks?\b|\bholding\b'),
    'advertising_mix':(r'\badvertis\w*\b|\bmedia\b',r'\bbudget\b|\baudien\w*\b|\breach\b'),
    'energy_dispatch':(r'\bpower\b|\belectric\w*\b',r'\bgenerat\w*\b|\bdispatch\w*\b|\bgrid\b'),
}


def anchors(text):
    result=[]
    for name,patterns in TEMPLATES.items():
        matches=[re.search(p,text,re.I) for p in patterns]
        if all(matches):result.append({'template':name,'evidence':[{'start':m.start(),'end':m.end(),'text':m.group()} for m in matches]})
    return result


def merge_semantic_templates(records,components,existing_edges):
    parent={r['id']:r['id'] for r in records}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):parent[find(b)]=find(a)
    for c in components:
        for member in c['members'][1:]:union(c['members'][0],member)
    first={};reviews=[];edges=list(existing_edges)
    for r in records:
        found=anchors(r['text']);reviews.append({'id':r['id'],'anchors':found,'unrecognized_semantics_certified':False})
        for item in found:
            name=item['template']
            if name in first:
                union(first[name],r['id']);edges.append({'left':first[name],'right':r['id'],'reason':'conservative_semantic_template:'+name,'similarity':None})
            else:first[name]=r['id']
    groups={}
    for r in records:groups.setdefault(find(r['id']),[]).append(r['id'])
    output=[];membership={}
    for members in groups.values():
        members=sorted(members);fid='operational_family_'+digest(members)[:12]
        output.append({'id':fid,'members':members});membership.update({m:fid for m in members})
    return sorted(output,key=lambda f:f['id']),membership,edges,reviews
