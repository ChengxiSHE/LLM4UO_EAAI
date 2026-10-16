"""Machine-readable MILP/teacher output contracts; semantic checks stay separate."""
from copy import deepcopy
from .contracts import ID,NUMBER,TEXT,obj,validate
from .milp_schema import model

COEFS={'type':'object','maxProperties':2000,'propertyNames':ID,'additionalProperties':NUMBER}
MODEL_SCHEMA=obj({'schema':{'const':'milp-v1'},'variables':{'type':'array','minItems':1,'maxItems':2000,
    'items':obj({'id':ID,'meaning':TEXT,'unit':TEXT,'domain':{'enum':['continuous','integer','binary']},
                 'lower':{'anyOf':[NUMBER,{'type':'null'}]},'upper':{'anyOf':[NUMBER,{'type':'null'}]}})},
    'constraints':{'type':'array','maxItems':10000,'items':obj({'id':ID,'coefficients':COEFS,'sense':{'enum':['le','ge','eq']},'rhs':NUMBER})},
    'objective':obj({'coefficients':COEFS,'sense':{'enum':['min','max']},'unit':TEXT,'offset':NUMBER})})
HASH={'type':'string','pattern':'^[a-f0-9]{64}$'}
TEACHER_SCHEMA=obj({'schema':{'const':'teacher-milp-v1'},'status':{'enum':['repair','no_witness','unresolved']},
    'input_sha256':HASH,'model_hashes':obj({'initial':HASH,'teacher':HASH}),
    'quote':obj({'field':{'type':'string','maxLength':300},'text':{'type':'string','minLength':1,'maxLength':20000},
                 'start':{'type':'integer','minimum':0},'end':{'type':'integer','minimum':1}}),
    'interpretation':{'type':'string','minLength':1,'maxLength':2000},
    'edits':{'type':'array','maxItems':4,'items':obj({'kind':{'enum':['row','domain','objective']},'target':ID})},
    'positive_examples':{'type':'array','maxItems':8,'items':COEFS}})
for schema in (MODEL_SCHEMA,TEACHER_SCHEMA):schema['$schema']='https://json-schema.org/draft/2020-12/schema'


def validate_output(value,teacher=False):
    checked=validate(value,TEACHER_SCHEMA if teacher else MODEL_SCHEMA)
    return checked if teacher else model(checked)
