"""Evaluator-only, hand-transcribed models from public inputs, never from labels.

These templates are reference preparation, not an inference model generator.
No import from a harness/teacher is permitted. Scope/assumptions accompany each.
"""
import itertools
import math
from copy import deepcopy

from .benchmark_inputs import input_shape_issues, payload_sha256, validate_public_input
from .milp_schema import model
from .schema import Invalid, digest

SUPPORTED = {'Knapsack', 'MediaSelectionProblem', 'cell', 'cut', 'prod', 'steel3', 'steel4',
             'diet', 'dietu', 'TSP', 'netasgn', 'multi', 'transp', 'nltrans'}


def build_reference(payload):
    p = validate_public_input(payload)
    name = p['id'].removeprefix('complexor_')
    if name not in SUPPORTED or len(p['instances']) != 1 or input_shape_issues(p):
        raise Invalid('unsupported_or_ambiguous_reference_input')
    d = p['instances'][0]['input']; vs = []; rows = []; costs = {}; sense = 'min'; notes = []
    def var(name, cost=0, domain='continuous', lower=0, upper=None, unit='input_quantity_units'):
        vs.append(dict(id=name, meaning=name, unit=unit, domain=domain, lower=lower, upper=upper)); costs[name] = cost
        return name
    def row(coefficients, direction, rhs):
        rows.append(dict(id='r'+str(len(rows)), coefficients=coefficients, sense=direction, rhs=rhs))
    if name in {'Knapsack', 'MediaSelectionProblem'}:
        if name == 'Knapsack':
            sense = 'max'; n = d['TotalItems']; c = d['ItemValues']
            ids = [var(f'select_{i}', c[i], 'binary', unit='item_selection') for i in range(n)]
            row(dict(zip(ids,d['ItemWeights'])), 'le', d['MaxKnapsackWeight'])
            notes.append('Each available item can be selected at most once; no unbounded-knapsack reinterpretation.')
        else:
            ids = [var(f'select_{i}', d['CostOfMedia'][i], 'binary', unit='media_selection') for i in range(d['AdvertisingMedia'])]
            for a in d['Incidence']: row(dict(zip(ids,a)), 'ge', 1)
    elif name == 'cell':
        sense = 'max'
        towers = [var(f'tower_{i}', 0, 'binary') for i in range(d['Tower'])]
        regions = [var(f'region_{j}', d['Population'][j], 'binary') for j in range(d['Region'])]
        row(dict(zip(towers,d['Cost'])), 'le', d['Budget'])
        for j,y in enumerate(regions): row({y:1,**{t:-d['Delta'][i][j] for i,t in enumerate(towers)}}, 'le', 0)
        notes.append('Objective is covered population, not percentage; any native percentage label needs an explicit conversion.')
    elif name == 'cut':
        ids = [var(f'pattern_{j}',1,'integer') for j in range(d['NumPatterns'])]
        for j in range(d['NumPatterns']):
            if sum(d['Widths'][i]*d['NumRollsWidthPattern'][i][j] for i in range(d['NumWidths'])) > d['RollWidth']:
                raise Invalid('pattern_exceeds_roll_width')
        for a,b in zip(d['NumRollsWidthPattern'],d['Orders']): row(dict(zip(ids,a)), 'ge', b)
        notes.append('At least each order quantity is fulfilled using only the supplied physically valid patterns.')
    elif name in {'prod','steel3','steel4'}:
        sense = 'max'
        if name == 'prod': n,c,lo,hi = d['ElementNum'],d['ProfitCoefficientC'],[0]*d['ElementNum'],d['UpperBoundU']
        elif name == 'steel3': n,c,lo,hi=d['ProductNum'],d['ProfitPerTon'],d['MinimumSale'],d['MaximumSale']
        else: n,c,lo,hi=d['NumProducts'],d['ProfitPerTon'],d['MinCommitment'],d['MaxMarketLimit']
        ids=[var(f'quantity_{i}',c[i],lower=lo[i],upper=hi[i]) for i in range(n)]
        if name=='prod': row({v:1/d['CoefficientA'][i] for i,v in enumerate(ids)},'le',d['GlobalParameterB'])
        elif name=='steel3': row({v:1/d['ProductionRate'][i] for i,v in enumerate(ids)},'le',d['AvailableHours'])
        else:
            for s in range(d['NumStages']): row({v:1/d['ProductionRate'][i][s] for i,v in enumerate(ids)},'le',d['StageAvailability'][s])
    elif name in {'diet','dietu'}:
        if name=='diet': n,k,c,aa,nlo,nhi=d['FoodCount'],d['NutrientCount'],d['Cost'],d['AmountNutrient'],d['NutrientMin'],d['NutrientMax']
        else: n,k,c,aa,nlo,nhi=d['FoodNum'],d['NutrientNum'],d['CostPerFood'],d['AmountPerNutrient'],d['MinReqAmount'],d['MaxReqAmount']
        ids=[var(f'food_{j}',c[j],lower=d['FoodMin'][j],upper=d['FoodMax'][j]) for j in range(n)]
        for i in range(k):
            a={v:aa[j][i] for j,v in enumerate(ids)}
            row(a,'ge',nlo[i]); row(a,'le',nhi[i])
        notes.append('Stored nutrient arrays are food x nutrient, explicitly transposed into nutrient constraint rows; amounts are divisible.')
    elif name=='multi':
        x={}
        for i,j,k in itertools.product(range(d['OriginNum']),range(d['DestinationNum']),range(d['ProductNum'])):
            x[i,j,k]=var(f'flow_{i}_{j}_{k}',d['Cost'][i][j][k])
        for i,k in itertools.product(range(d['OriginNum']),range(d['ProductNum'])):
            row({x[i,j,k]:1 for j in range(d['DestinationNum'])},'eq',d['Supply'][i][k])
        for j,k in itertools.product(range(d['DestinationNum']),range(d['ProductNum'])):
            row({x[i,j,k]:1 for i in range(d['OriginNum'])},'eq',d['Demand'][k][j])
        for i,j in itertools.product(range(d['OriginNum']),range(d['DestinationNum'])):
            row({x[i,j,k]:1 for k in range(d['ProductNum'])},'le',d['Limit'][i][j])
        notes.append('Demand stored product x destination; supply stored origin x product. Goods treated as divisible; balances are equalities as stated.')
    else:
        if name=='TSP': n,k,supply,demand,c,limit=d['OriginNum'],d['DestinationNum'],d['Supply'],d['Demand'],d['Cost'],None
        elif name=='transp': n,k,supply,demand,c,limit=d['NumberOfOrigins'],d['NumberOfDestinations'],d['SupplyOfOrigin'],d['DemandOfDestination'],d['CostPerUnit'],None
        elif name=='nltrans': n,k,supply,demand,c,limit=d['Origins'],d['Destinations'],d['Supply'],d['Demand'],d['Rate'],d['Limit']
        else: n,k,supply,demand,c,limit=d['People'],d['Projects'],d['Supply'],d['Demand'],d['Cost'],d['Limit']
        x={(i,j):var(f'flow_{i}_{j}',c[i][j],upper=None if limit is None else limit[i][j]) for i in range(n) for j in range(k)}
        exact=name in {'transp','netasgn'}
        for i in range(n): row({x[i,j]:1 for j in range(k)},'eq' if exact else 'le',supply[i])
        for j in range(k): row({x[i,j]:1 for i in range(n)},'eq' if exact else 'ge',demand[j])
        notes.append('Divisible quantities/hours. Supply/demand equalities only where explicitly stated; otherwise supply upper and demand lower bounds.')
        if name in {'TSP','nltrans'}: notes.append('Follow the distributed linear transportation text, not an interpretation of the folder name.')
    m=model(dict(schema='milp-v1',variables=vs,constraints=rows,
                 objective=dict(coefficients=costs,sense=sense,unit='source_objective_units',offset=0)))
    return dict(schema='input-bound-reference-model-v1',problem_id=p['id'],input_sha256=payload_sha256(p),
                model=m,model_sha256=digest(m),assumptions=notes,
                preparation='assistant_transcribed_from_public_input_before_native_label_comparison',
                expert_semantic_certification=False)
