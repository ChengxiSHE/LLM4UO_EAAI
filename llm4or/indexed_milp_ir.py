"""Bounded, benchmark-agnostic expansion of indexed linear-model IR.

The module deliberately interprets a small data language.  It does not infer a
formulation, execute generated code, or repair a candidate.  Admission means
only that deterministic expansion produced a valid, resource-bounded milp-v1
object.
"""

import itertools
import math

from .milp_schema import model as validate_milp
from .schema import Invalid, canonical, digest, identifier


IR_SCHEMA = "indexed-milp-ir-v1"
ADMISSION_SCHEMA = "indexed-milp-ir-v1-admission"
COMPILER_IDENTITY = "indexed-milp-ir-compiler-v1"
MAX_IR_BYTES = 32_768
LIMIT_KEYS = {
    "variables", "constraints", "nonzeros", "serialized_bytes",
    "expansion_steps",
}
TOP_LEVEL_KEYS = {
    "schema", "data_parameter", "sets", "variables", "constraints", "objective",
}


class IRCompileError(ValueError):
    """A stable fail-closed code followed by optional diagnostic context."""


def _fail(code, detail=""):
    suffix = f": {detail}" if detail else ""
    raise IRCompileError(f"{code}{suffix}")


def _exact(value, expected, code):
    if not isinstance(value, dict) or set(value) != set(expected):
        _fail(code)


def _sequence(value, code):
    if not isinstance(value, list):
        _fail(code)
    return value


def _with_defaults(value, required, defaults, code):
    if (
        not isinstance(value, dict) or not set(required) <= set(value)
        or not set(value) <= set(required) | set(defaults)
    ):
        _fail(code)
    result = dict(defaults)
    result.update(value)
    return result


def _finite(value, code="finite_number"):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
        _fail(code)
    return float(value)


def _integer(value, code="integer_required"):
    if type(value) is not int:
        _fail(code)
    return value


def validate_ir_surface(ir):
    """Validate only the bounded immutable envelope, before reviewer repair."""
    _exact(ir, TOP_LEVEL_KEYS, "ir_keys")
    if ir["schema"] != IR_SCHEMA:
        _fail("ir_schema")
    if ir["data_parameter"] != "instance_data":
        _fail("data_parameter")
    if (
        not isinstance(ir["sets"], list)
        or not isinstance(ir["variables"], list)
        or not isinstance(ir["constraints"], list)
        or not isinstance(ir["objective"], dict)
    ):
        _fail("ir_surface_shape")
    try:
        raw = canonical(ir).encode()
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        _fail("canonical_input", str(exc))
    if len(raw) > MAX_IR_BYTES:
        _fail("resource_ir_bytes")
    return {"ir_sha256": digest(ir), "ir_bytes": len(raw)}


class _Compiler:
    def __init__(self, data, ir, limits):
        if not isinstance(data, (dict, list)):
            _fail("data_root")
        _exact(limits, LIMIT_KEYS, "resource_limit_keys")
        self.limits = {}
        for name in sorted(LIMIT_KEYS):
            value = limits[name]
            if type(value) is not int or value < 1:
                _fail("resource_limit_value", name)
            self.limits[name] = value
        self.data = data
        self.ir = ir
        self.steps = 0
        self.sets = {}
        self.families = {}
        self.variable_ids = set()

    def step(self, amount=1):
        self.steps += amount
        if self.steps > self.limits["expansion_steps"]:
            _fail("resource_expansion_steps")

    def data_path(self, path, env):
        if not isinstance(path, list) or not path:
            _fail("data_path")
        path = list(path)
        if path[:1] == ["instance_data"]:
            path = path[1:]
        if not path:
            _fail("data_path")
        if len(path) == 1 and isinstance(path[0], str) and path[0] in env:
            return env[path[0]]
        value = self.data
        for position, raw in enumerate(path):
            self.step()
            if isinstance(raw, dict):
                component = self.num(raw, env)
            elif position > 0 and isinstance(raw, str) and raw in env:
                component = env[raw]
            else:
                component = raw
            if type(component) is float and component.is_integer():
                component = int(component)
            if isinstance(value, dict):
                if not isinstance(component, str) or component not in value:
                    _fail("data_path")
                value = value[component]
            elif isinstance(value, list):
                if type(component) is not int or component < 0 or component >= len(value):
                    _fail("data_path")
                value = value[component]
            else:
                _fail("data_path")
        return value

    def bindings(self, specs, env=None, indices=()):
        specs = _sequence(specs, "binding_list")
        env = {} if env is None else dict(env)
        declared = []
        for spec in specs:
            if isinstance(spec, dict) and set(spec) in ({"name", "set"}, {"name", "set", "where"}):
                declared.append(spec["name"])
            elif (
                isinstance(spec, dict)
                and set(spec) in ({"unpack", "set"}, {"unpack", "set", "where"})
                and isinstance(spec["unpack"], list)
            ):
                declared.extend(spec["unpack"])
        if len(declared) != len(set(declared)):
            _fail("duplicate_binding")

        def visit(position, current, current_indices):
            self.step()
            if position == len(specs):
                yield current, current_indices
                return
            spec = specs[position]
            if not isinstance(spec, dict) or "set" not in spec:
                _fail("binding_keys")
            set_name = spec["set"]
            if not isinstance(set_name, str) or set_name not in self.sets:
                _fail("unknown_set")
            if set(spec) in ({"name", "set"}, {"name", "set", "where"}):
                names = [spec["name"]]
                unpack = False
            elif set(spec) in ({"unpack", "set"}, {"unpack", "set", "where"}):
                names = spec["unpack"]
                if (not isinstance(names, list) or not names or
                        any(not isinstance(x, str) or not x for x in names) or
                        len(names) != len(set(names))):
                    _fail("binding_unpack")
                unpack = True
            else:
                _fail("binding_keys")
            for member in self.sets[set_name]:
                self.step()
                if unpack:
                    if not isinstance(member, tuple) or len(member) != len(names):
                        _fail("binding_arity")
                    values = member
                else:
                    values = (member,)
                next_env = dict(current)
                next_env.update(zip(names, values))
                if self.pred(spec.get("where", True), next_env):
                    yield from visit(position + 1, next_env, current_indices + tuple(values))

        yield from visit(0, env, tuple(indices))

    def aggregate(self, expr, env, predicate=False):
        if predicate:
            expr = _with_defaults(
                expr, {"aggregate", "over", "predicate"}, {"where": True},
                "predicate_keys",
            )
            kind = expr["aggregate"]
            if kind not in {"any", "all"}:
                _fail("predicate_aggregate")
        else:
            expr = _with_defaults(
                expr, {"aggregate", "over", "value"}, {"where": True},
                "numeric_keys",
            )
            kind = expr["aggregate"]
            if kind not in {"sum", "min", "max"}:
                _fail("numeric_aggregate")
        values = []
        for inner, _ in self.bindings(expr["over"], env):
            if self.pred(expr["where"], inner):
                values.append(
                    self.pred(expr["predicate"], inner) if predicate
                    else self.num(expr["value"], inner)
                )
        if kind == "sum":
            return float(sum(values))
        if kind == "any":
            return any(values)
        if kind == "all":
            return all(values)
        if not values:
            _fail("empty_aggregate")
        return float(min(values) if kind == "min" else max(values))

    def num(self, expr, env):
        self.step()
        if type(expr) in (int, float):
            return _finite(expr)
        if isinstance(expr, str):
            if expr not in env:
                _fail("unknown_env")
            return _finite(env[expr])
        if not isinstance(expr, dict):
            _fail("numeric_expression")
        if set(expr) in ({"env"}, {"name"}):
            name = expr.get("env", expr.get("name"))
            if not isinstance(name, str) or name not in env:
                _fail("unknown_env")
            return _finite(env[name])
        if set(expr) == {"data"}:
            return _finite(self.data_path(expr["data"], env))
        if set(expr) == {"op", "args"}:
            op = expr["op"]
            args = _sequence(expr["args"], "numeric_args")
            values = [self.num(value, env) for value in args]
            if op in {"add", "mul", "min", "max"} and not values:
                _fail("numeric_arity")
            if op in {"sub", "div"} and len(values) != 2:
                _fail("numeric_arity")
            if op in {"neg", "sqrt"} and len(values) != 1:
                _fail("numeric_arity")
            if op == "add":
                result = sum(values)
            elif op == "mul":
                result = math.prod(values)
            elif op == "sub":
                result = values[0] - values[1]
            elif op == "div":
                if values[1] == 0:
                    _fail("division_by_zero")
                result = values[0] / values[1]
            elif op == "neg":
                result = -values[0]
            elif op == "sqrt":
                if values[0] < 0:
                    _fail("sqrt_domain")
                result = math.sqrt(values[0])
            elif op == "min":
                result = min(values)
            elif op == "max":
                result = max(values)
            else:
                _fail("numeric_operator")
            return _finite(result)
        if set(expr) == {"if"}:
            branch = expr["if"]
            _exact(branch, {"condition", "then", "else"}, "conditional_keys")
            return self.num(branch["then"] if self.pred(branch["condition"], env) else branch["else"], env)
        if "aggregate" in expr:
            return self.aggregate(expr, env, predicate=False)
        _fail("numeric_keys")

    def pred(self, expr, env):
        self.step()
        if type(expr) is bool:
            return expr
        if not isinstance(expr, dict):
            _fail("predicate_expression")
        if set(expr) == {"compare", "left", "right"}:
            left, right = self.num(expr["left"], env), self.num(expr["right"], env)
            operations = {
                "eq": left == right, "ne": left != right,
                "lt": left < right, "le": left <= right,
                "gt": left > right, "ge": left >= right,
            }
            if expr["compare"] not in operations:
                _fail("predicate_compare")
            return operations[expr["compare"]]
        if set(expr) == {"logic", "args"}:
            op = expr["logic"]
            args = _sequence(expr["args"], "predicate_args")
            if op == "not":
                if len(args) != 1:
                    _fail("predicate_arity")
                return not self.pred(args[0], env)
            if op not in {"and", "or"} or not args:
                _fail("predicate_operator")
            values = [self.pred(value, env) for value in args]
            return all(values) if op == "and" else any(values)
        if "aggregate" in expr:
            return self.aggregate(expr, env, predicate=True)
        _fail("predicate_keys")

    def build_sets(self, declarations):
        for declaration in _sequence(declarations, "sets_list"):
            if not isinstance(declaration, dict):
                _fail("set_keys")
            kind = declaration.get("kind")
            if kind == "range":
                _exact(declaration, {"id", "kind", "start", "stop"}, "set_keys")
                start = self.num(declaration["start"], {})
                stop = self.num(declaration["stop"], {})
                if not start.is_integer() or not stop.is_integer():
                    _fail("range_integer")
                if start < 0 or stop < start:
                    _fail("range_bounds")
                members = tuple(range(int(start), int(stop)))
            elif kind == "records":
                _exact(declaration, {"id", "kind", "path", "arity"}, "set_keys")
                arity = _integer(declaration["arity"], "record_arity")
                if arity < 1:
                    _fail("record_arity")
                raw = self.data_path(declaration["path"], {})
                if not isinstance(raw, list):
                    _fail("record_set")
                records = []
                for row in raw:
                    self.step()
                    if not isinstance(row, list) or len(row) != arity:
                        _fail("record_arity")
                    records.append(tuple(row))
                members = tuple(records)
            else:
                _fail("set_kind")
            set_id = declaration.get("id")
            try:
                identifier(set_id)
            except Invalid as exc:
                _fail("set_id", str(exc))
            if set_id in self.sets:
                _fail("duplicate_set")
            self.sets[set_id] = members

    @staticmethod
    def generated_id(base, indices):
        try:
            identifier(base)
        except Invalid as exc:
            _fail("base_id", str(exc))
        clean = []
        for value in indices:
            if type(value) is not int or value < 0:
                _fail("generated_index")
            clean.append(str(value))
        result = base if not clean else base + "_" + "_".join(clean)
        try:
            identifier(result)
        except Invalid as exc:
            _fail("generated_id", str(exc))
        return result

    def build_variables(self, declarations):
        rows = []
        for declaration in _sequence(declarations, "variables_list"):
            declaration = _with_defaults(
                declaration, {"id", "meaning", "domain"},
                {"unit": "unit", "forall": [], "where": True, "lower": None, "upper": None},
                "variable_keys",
            )
            family = declaration["id"]
            try:
                identifier(family)
            except Invalid as exc:
                _fail("variable_family", str(exc))
            if family in self.families:
                _fail("duplicate_variable_family")
            self.families[family] = {}
            for env, indices in self.bindings(declaration["forall"]):
                if not self.pred(declaration["where"], env):
                    continue
                var_id = self.generated_id(family, indices)
                if var_id in self.variable_ids:
                    _fail("duplicate_variable_id")
                lower = None if declaration["lower"] is None else self.num(declaration["lower"], env)
                upper = None if declaration["upper"] is None else self.num(declaration["upper"], env)
                row = {
                    "id": var_id, "meaning": declaration["meaning"],
                    "unit": declaration["unit"], "domain": declaration["domain"],
                    "lower": lower, "upper": upper,
                }
                rows.append(row)
                self.variable_ids.add(var_id)
                self.families[family][tuple(indices)] = var_id
                if len(rows) > self.limits["variables"]:
                    _fail("resource_variables")
        if not rows:
            _fail("no_variables")
        return rows

    def add_terms(self, terms, outer_env):
        coefficients = {}
        for term in _sequence(terms, "terms_list"):
            term = _with_defaults(
                term, {"family"},
                {"indices": [], "coefficient": 1, "sum": [], "where": True},
                "term_keys",
            )
            family = term["family"]
            if not isinstance(family, str) or family not in self.families:
                _fail("unknown_variable_family")
            for env, _ in self.bindings(term["sum"], outer_env):
                if not self.pred(term["where"], env):
                    continue
                raw_indices = _sequence(term["indices"], "term_indices")
                indices = []
                for expr in raw_indices:
                    value = self.num(expr, env)
                    if not value.is_integer() or value < 0:
                        _fail("variable_index")
                    indices.append(int(value))
                key = tuple(indices)
                if key not in self.families[family]:
                    _fail("unknown_variable_reference")
                var_id = self.families[family][key]
                coefficient = self.num(term["coefficient"], env)
                coefficients[var_id] = _finite(coefficients.get(var_id, 0.0) + coefficient)
        return {name: value for name, value in sorted(coefficients.items()) if value != 0}

    def build_constraints(self, declarations):
        rows = []
        ids = set()
        for declaration in _sequence(declarations, "constraints_list"):
            declaration = _with_defaults(
                declaration, {"id", "terms", "sense", "rhs"},
                {"forall": [], "where": True}, "constraint_keys",
            )
            for env, indices in self.bindings(declaration["forall"]):
                if not self.pred(declaration["where"], env):
                    continue
                row_id = self.generated_id(declaration["id"], indices)
                if row_id in ids:
                    _fail("duplicate_constraint_id")
                ids.add(row_id)
                rows.append({
                    "id": row_id,
                    "coefficients": self.add_terms(declaration["terms"], env),
                    "sense": declaration["sense"],
                    "rhs": self.num(declaration["rhs"], env),
                })
                if len(rows) > self.limits["constraints"]:
                    _fail("resource_constraints")
        return rows

    def build_objective(self, declaration):
        declaration = _with_defaults(
            declaration, {"terms", "sense"}, {"unit": "unit", "offset": 0},
            "objective_keys",
        )
        sense = {"minimize": "min", "maximize": "max"}.get(
            declaration["sense"], declaration["sense"],
        )
        return {
            "coefficients": self.add_terms(declaration["terms"], {}),
            "sense": sense,
            "unit": declaration["unit"],
            "offset": self.num(declaration["offset"], {}),
        }

    def compile(self):
        surface = validate_ir_surface(self.ir)
        ir_bytes = surface["ir_bytes"]
        ir_hash = surface["ir_sha256"]
        try:
            data_hash = digest(self.data)
        except (TypeError, ValueError, RecursionError, OverflowError) as exc:
            _fail("canonical_input", str(exc))
        self.build_sets(self.ir["sets"])
        variables = self.build_variables(self.ir["variables"])
        constraints = self.build_constraints(self.ir["constraints"])
        objective = self.build_objective(self.ir["objective"])
        candidate = {
            "schema": "milp-v1", "variables": variables,
            "constraints": constraints, "objective": objective,
        }
        nonzeros = sum(len(row["coefficients"]) for row in constraints) + len(objective["coefficients"])
        if nonzeros > self.limits["nonzeros"]:
            _fail("resource_nonzeros")
        serialized_bytes = len(canonical(candidate).encode())
        if serialized_bytes > self.limits["serialized_bytes"]:
            _fail("resource_serialized_bytes")
        try:
            admitted = validate_milp(candidate)
        except Invalid as exc:
            _fail("milp_validation", str(exc))
        metrics = {
            "variables": len(variables), "constraints": len(constraints),
            "nonzeros": nonzeros, "serialized_bytes": serialized_bytes,
            "expansion_steps": self.steps, "ir_bytes": ir_bytes,
        }
        return {
            "schema": ADMISSION_SCHEMA, "status": "admitted",
            "compiler_identity": COMPILER_IDENTITY,
            "data_sha256": data_hash, "ir_sha256": ir_hash,
            "model_sha256": digest(admitted), "model": admitted,
            "metrics": metrics, "resource_limits": dict(self.limits),
        }


def compile_ir(data, ir, limits):
    """Expand and admit one IR candidate, or raise :class:`IRCompileError`."""

    return _Compiler(data, ir, limits).compile()
