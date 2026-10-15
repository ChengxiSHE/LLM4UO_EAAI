"""Translate a restricted Gurobi-flavoured Python AST into ``milp-v1``.

This module never imports or executes generated Python.  It interprets a small,
explicit AST language used by the official Text2Opt reference programs and
emits the repository's bounded sparse model contract.  Unsupported syntax,
nonlinear expressions, excessive work, and ambiguous model construction fail
closed.
"""

from __future__ import annotations

import ast
import itertools
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from .milp_schema import MAX_NNZ, MAX_ROWS, MAX_VARS, model as validate_model
from .schema import Invalid

MAX_CODE_BYTES = 2_000_000
MAX_AST_NODES = 500_000
MAX_STEPS = 2_000_000
MAX_RANGE = 100_000
MAX_COLLECTION = 200_000
MAX_MODELS = 128


class RestrictedCodeError(Invalid):
    pass


def _finite(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e12:
        raise RestrictedCodeError("finite bounded numeric value required")
    return float(value)


@dataclass(frozen=True)
class _Expr:
    coefficients: dict[str, float]
    constant: float = 0.0

    def _combine(self, other: Any, sign: float) -> "_Expr":
        rhs = _as_expr(other)
        values = dict(self.coefficients)
        for key, value in rhs.coefficients.items():
            values[key] = values.get(key, 0.0) + sign * value
            if values[key] == 0:
                values.pop(key)
        if len(values) > MAX_NNZ:
            raise RestrictedCodeError("expression nonzero limit")
        return _Expr(values, _finite(self.constant + sign * rhs.constant))

    def __add__(self, other: Any) -> "_Expr":
        return self._combine(other, 1.0)

    def __radd__(self, other: Any) -> "_Expr":
        return _as_expr(other)._combine(self, 1.0)

    def __sub__(self, other: Any) -> "_Expr":
        return self._combine(other, -1.0)

    def __rsub__(self, other: Any) -> "_Expr":
        return _as_expr(other)._combine(self, -1.0)

    def __neg__(self) -> "_Expr":
        return self * -1

    def __mul__(self, other: Any) -> "_Expr":
        if isinstance(other, _Expr):
            raise RestrictedCodeError("nonlinear expression")
        scalar = _finite(other)
        return _Expr({k: _finite(v * scalar) for k, v in self.coefficients.items()},
                     _finite(self.constant * scalar))

    def __rmul__(self, other: Any) -> "_Expr":
        return self * other

    def __truediv__(self, other: Any) -> "_Expr":
        scalar = _finite(other)
        if scalar == 0:
            raise RestrictedCodeError("division by zero")
        return self * (1.0 / scalar)

    def __le__(self, other: Any) -> "_Constraint":
        return _Constraint(self - other, "le")

    def __ge__(self, other: Any) -> "_Constraint":
        return _Constraint(self - other, "ge")

    def __eq__(self, other: Any) -> "_Constraint":  # type: ignore[override]
        return _Constraint(self - other, "eq")

    def __bool__(self) -> bool:
        raise RestrictedCodeError("symbolic expression cannot be a condition")


def _as_expr(value: Any) -> _Expr:
    if isinstance(value, _Expr):
        return value
    return _Expr({}, _finite(value))


@dataclass(frozen=True)
class _Constraint:
    expression: _Expr
    sense: str

    def __bool__(self) -> bool:
        raise RestrictedCodeError("symbolic constraint cannot be a condition")


class _Var(_Expr):
    def __init__(self, identifier: str, original_name: str, lower: float | None,
                 upper: float | None, domain: str):
        object.__setattr__(self, "coefficients", {identifier: 1.0})
        object.__setattr__(self, "constant", 0.0)
        object.__setattr__(self, "identifier", identifier)
        object.__setattr__(self, "original_name", original_name)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "domain", domain)
        object.__setattr__(self, "solution_value", None)

    @property
    def ub(self) -> float | None:
        return self.upper

    @ub.setter
    def ub(self, value: Any) -> None:
        object.__setattr__(self, "upper", None if value is None else _finite(value))

    @property
    def X(self) -> float:
        if self.solution_value is None:
            raise RestrictedCodeError("solution value unavailable")
        return self.solution_value

    @property
    def x(self) -> float:
        return self.X


class _GRB:
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BINARY = "binary"
    MINIMIZE = "min"
    MAXIMIZE = "max"
    INFINITY = None
    OPTIMAL = 2
    INFEASIBLE = 3
    INF_OR_UNBD = 4
    UNBOUNDED = 5


GRB = _GRB()


class _GP:
    """Marker for the narrowly supported ``import gurobipy as gp`` surface."""


GP = _GP()


class _Params:
    def __init__(self, model: "_Model"):
        object.__setattr__(self, "model", model)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name not in {
            "OutputFlag", "TimeLimit", "MIPFocus", "Threads", "Presolve", "Method",
            "DualReductions",
        }:
            raise RestrictedCodeError("unsupported solver parameter")
        self.model.setParam(name, value)


@dataclass(frozen=True)
class _SafeFile:
    payload: Any


class _SafeJSON:
    @staticmethod
    def load(handle: Any) -> Any:
        if not isinstance(handle, _SafeFile):
            raise RestrictedCodeError("json.load requires an injected data handle")
        return json.loads(json.dumps(handle.payload, allow_nan=False))


class _Model:
    def __init__(self, name: str = "model"):
        self.name = str(name)
        self.variables: list[_Var] = []
        self.constraints: list[_Constraint] = []
        self.objective = _Expr({})
        self.objective_sense = "min"
        self.optimized = False
        self.params = _Params(self)
        self.solution_status: str | None = None
        self.solution_objective: float | None = None
        self.solution_point: dict[str, float] | None = None

    def addVar(self, lb: Any = 0.0, ub: Any = None, obj: Any = 0.0,
               vtype: Any = GRB.CONTINUOUS, name: Any = None, **kwargs: Any) -> _Var:
        if kwargs:
            raise RestrictedCodeError("unsupported addVar keyword")
        if len(self.variables) >= MAX_VARS:
            raise RestrictedCodeError("variable limit")
        domain = str(vtype)
        if domain not in {"continuous", "integer", "binary"}:
            raise RestrictedCodeError("unsupported variable domain")
        identifier = f"v{len(self.variables):06d}"
        original = str(name) if name is not None else identifier
        lower = None if lb is None else _finite(lb)
        upper = None if ub is None else _finite(ub)
        variable = _Var(identifier, original[:500], lower, upper, domain)
        self.variables.append(variable)
        coefficient = _finite(obj)
        if coefficient:
            self.objective = self.objective + coefficient * variable
        return variable

    def addVars(self, *indices: Any, lb: Any = 0.0, ub: Any = None, obj: Any = 0.0,
                vtype: Any = GRB.CONTINUOUS, name: Any = "x", **kwargs: Any) -> dict[Any, _Var]:
        if kwargs or not indices:
            raise RestrictedCodeError("unsupported addVars arguments")
        axes = []
        for index in indices:
            if type(index) is int:
                axis = list(range(index))
            elif isinstance(index, (list, tuple, range, set)):
                axis = list(index)
            else:
                raise RestrictedCodeError("addVars index set")
            if len(axis) > MAX_RANGE:
                raise RestrictedCodeError("addVars index limit")
            axes.append(axis)
        keys: list[Any] = []
        def expand(depth: int, prefix: tuple[Any, ...]) -> None:
            if depth == len(axes):
                keys.append(prefix[0] if len(prefix) == 1 else prefix)
                return
            for item in axes[depth]:
                # Gurobi flattens tuple-list members when additional index
                # axes are supplied: addVars([(i,j)], K) is keyed by (i,j,k).
                if isinstance(item, list):
                    item = tuple(item)
                expand(depth + 1, prefix + (item if isinstance(item, tuple) else (item,)))
        expand(0, ())
        if len(keys) > MAX_VARS - len(self.variables):
            raise RestrictedCodeError("variable limit")
        result = {}
        def at(specification: Any, key: Any, label: str) -> Any:
            if isinstance(specification, (list, tuple)) and isinstance(key, int):
                if not 0 <= key < len(specification):
                    raise RestrictedCodeError("addVars missing " + label + " index")
                return specification[key]
            if not isinstance(specification, dict):
                return specification
            if key not in specification:
                raise RestrictedCodeError("addVars missing " + label + " key")
            return specification[key]
        for key in keys:
            suffix = key if isinstance(key, tuple) else (key,)
            base_name = at(name, key, "name")
            variable_name = (
                str(base_name) if isinstance(name, dict)
                else f"{base_name}[{','.join(str(x) for x in suffix)}]"
            )
            result[key] = self.addVar(
                lb=at(lb, key, "lb"), ub=at(ub, key, "ub"), obj=at(obj, key, "obj"),
                vtype=at(vtype, key, "vtype"), name=variable_name,
            )
        return result

    def addConstr(self, constraint: Any, name: Any = None, **kwargs: Any) -> _Constraint:
        if kwargs:
            raise RestrictedCodeError("unsupported addConstr keyword")
        if type(constraint) is bool:
            constraint = _Constraint(_Expr({}, 0.0 if constraint else 1.0), "le")
        if not isinstance(constraint, _Constraint):
            raise RestrictedCodeError("addConstr expects a linear comparison")
        if len(self.constraints) >= MAX_ROWS:
            raise RestrictedCodeError("constraint limit")
        self.constraints.append(constraint)
        return constraint

    def addConstrs(self, constraints: Any, name: Any = None, **kwargs: Any) -> list[_Constraint]:
        if kwargs:
            raise RestrictedCodeError("unsupported addConstrs keyword")
        values = list(constraints)
        if len(values) > MAX_ROWS - len(self.constraints):
            raise RestrictedCodeError("constraint limit")
        return [self.addConstr(value, name=name) for value in values]

    def setObjective(self, expression: Any, sense: Any = GRB.MINIMIZE) -> None:
        if sense not in {"min", "max"}:
            raise RestrictedCodeError("objective sense")
        self.objective = _as_expr(expression)
        self.objective_sense = sense

    def setParam(self, name: Any, value: Any) -> None:
        parameter = str(name)
        if parameter not in {"TimeLimit", "MIPFocus", "OutputFlag", "Threads", "Presolve", "Method"}:
            raise RestrictedCodeError("unsupported solver parameter")
        _finite(value)

    def optimize(self) -> None:
        self.optimized = True

    def update(self) -> None:
        return None

    def dispose(self) -> None:
        return None

    def apply_solution(self, result: dict[str, Any]) -> None:
        status = result.get("status")
        point = result.get("point")
        objective = result.get("objective")
        if not isinstance(status, str) or point is not None and not isinstance(point, dict):
            raise RestrictedCodeError("trusted solver result shape")
        self.solution_status = status
        self.solution_objective = None if objective is None else _finite(objective)
        self.solution_point = point
        if point is not None:
            for variable in self.variables:
                if variable.identifier not in point:
                    raise RestrictedCodeError("trusted solver point incomplete")
                object.__setattr__(variable, "solution_value", _finite(point[variable.identifier]))

    @property
    def Status(self) -> int:
        return {"optimal": GRB.OPTIMAL, "infeasible": GRB.INFEASIBLE,
                "unbounded": GRB.UNBOUNDED}.get(self.solution_status, GRB.INF_OR_UNBD)

    @property
    def status(self) -> int:
        return self.Status

    @property
    def ObjVal(self) -> float:
        if self.solution_objective is None:
            raise RestrictedCodeError("objective value unavailable")
        return self.solution_objective

    @property
    def objVal(self) -> float:
        return self.ObjVal

    @property
    def SolCount(self) -> int:
        return int(self.solution_point is not None)

    @property
    def Params(self) -> _Params:
        return self.params

    @property
    def ModelSense(self) -> str:
        return self.objective_sense

    @ModelSense.setter
    def ModelSense(self, value: Any) -> None:
        if value not in {GRB.MINIMIZE, GRB.MAXIMIZE}:
            raise RestrictedCodeError("objective sense")
        self.objective_sense = value

    def export(self) -> dict[str, Any]:
        rows = []
        for index, item in enumerate(self.constraints):
            rows.append({
                "id": f"r{index:06d}",
                "coefficients": item.expression.coefficients,
                "sense": item.sense,
                "rhs": _finite(-item.expression.constant),
            })
        value = {
            "schema": "milp-v1",
            "variables": [
                {
                    "id": var.identifier,
                    "meaning": var.original_name or var.identifier,
                    "unit": "1",
                    "domain": var.domain,
                    "lower": var.lower,
                    "upper": var.upper,
                }
                for var in self.variables
            ],
            "constraints": rows,
            "objective": {
                "coefficients": self.objective.coefficients,
                "sense": self.objective_sense,
                "unit": "1",
                "offset": _finite(self.objective.constant),
            },
        }
        return validate_model(value)


class _Return(Exception):
    def __init__(self, value: Any):
        self.value = value


class _Break(Exception):
    pass


class _Continue(Exception):
    pass


class _ModelReady(Exception):
    def __init__(self, model: _Model):
        self.model = model


@dataclass(frozen=True)
class _Function:
    node: ast.FunctionDef
    closure: dict[str, Any] | None = None
    nonlocal_names: tuple[str, ...] = ()


class _Environment(dict[str, Any]):
    def __init__(self, initial: dict[str, Any], nonlocal_names: tuple[str, ...]):
        super().__init__(initial)
        self.nonlocal_names = set(nonlocal_names)
        self.nonlocal_source = initial


@dataclass(frozen=True)
class _Lambda:
    node: ast.Lambda
    closure: dict[str, Any]


class _Itertools:
    pass


ITERTOOLS = _Itertools()


@dataclass(frozen=True)
class _ItertoolsFunction:
    name: str


class _SafeArray:
    """Small dense array facade for generated SciPy programs.

    It deliberately supports only indexing, scalar slice assignment, flattening,
    and reshape.  There is no NumPy import or arbitrary ufunc dispatch.
    """

    def __init__(self, values: Any, shape: tuple[int, ...] | None = None):
        if shape is None:
            shape, flat = self._flatten(values)
        else:
            flat = list(values)
        if not shape or any(type(value) is not int or value < 0 for value in shape):
            raise RestrictedCodeError("array shape")
        size = math.prod(shape)
        if size > MAX_COLLECTION or len(flat) != size:
            raise RestrictedCodeError("array size")
        self._shape = shape
        self._flat = flat

    @classmethod
    def _flatten(cls, values: Any) -> tuple[tuple[int, ...], list[Any]]:
        if not isinstance(values, (list, tuple, range, _SafeArray)):
            raise RestrictedCodeError("array values")
        if isinstance(values, _SafeArray):
            return values.shape, list(values._flat)
        rows = list(values)
        if len(rows) > MAX_COLLECTION:
            raise RestrictedCodeError("array size")
        if rows and isinstance(rows[0], (list, tuple, range, _SafeArray)):
            children = [cls._flatten(row) for row in rows]
            inner = children[0][0]
            if any(shape != inner for shape, _ in children):
                raise RestrictedCodeError("ragged array")
            return (len(rows),) + inner, [item for _, flat in children for item in flat]
        if any(isinstance(row, (list, tuple, range, _SafeArray)) for row in rows):
            raise RestrictedCodeError("ragged array")
        return (len(rows),), rows

    @property
    def shape(self) -> tuple[int, ...]:
        return self._shape

    @property
    def size(self) -> int:
        return len(self._flat)

    def __len__(self) -> int:
        return self._shape[0]

    def _offsets(self, key: Any) -> list[int]:
        keys = key if isinstance(key, tuple) else (key,)
        if len(keys) > len(self._shape):
            raise RestrictedCodeError("array index rank")
        axes: list[list[int]] = []
        for axis, extent in enumerate(self._shape):
            item = keys[axis] if axis < len(keys) else slice(None)
            if isinstance(item, slice):
                axes.append(list(range(extent))[item])
            else:
                index = int(_finite(item))
                if index < 0:
                    index += extent
                if not 0 <= index < extent:
                    raise RestrictedCodeError("array index")
                axes.append([index])
        offsets = []
        for coordinate in itertools.product(*axes):
            offset = 0
            for index, extent in zip(coordinate, self._shape):
                offset = offset * extent + index
            offsets.append(offset)
        return offsets

    def __getitem__(self, key: Any) -> Any:
        offsets = self._offsets(key)
        return self._flat[offsets[0]] if len(offsets) == 1 else [self._flat[i] for i in offsets]

    def __setitem__(self, key: Any, value: Any) -> None:
        offsets = self._offsets(key)
        if isinstance(value, (list, tuple, _SafeArray)):
            values = value._flat if isinstance(value, _SafeArray) else list(value)
            if len(values) != len(offsets):
                raise RestrictedCodeError("array assignment shape")
        else:
            values = [value] * len(offsets)
        for offset, item in zip(offsets, values):
            self._flat[offset] = item

    def ravel(self) -> "_SafeArray":
        return _SafeArray(self._flat, (len(self._flat),))

    def reshape(self, shape: Any) -> "_SafeArray":
        shape = tuple(shape) if isinstance(shape, (list, tuple)) else (int(_finite(shape)),)
        return _SafeArray(self._flat, tuple(int(_finite(x)) for x in shape))

    def tolist(self) -> Any:
        def build(flat: list[Any], shape: tuple[int, ...]) -> Any:
            if len(shape) == 1:
                return list(flat)
            step = math.prod(shape[1:])
            return [build(flat[i:i + step], shape[1:]) for i in range(0, len(flat), step)]
        return build(self._flat, self._shape)


class _Numpy:
    pass


NUMPY = _Numpy()


class _Math:
    inf = math.inf

    @staticmethod
    def sqrt(value: Any) -> float:
        return _finite(math.sqrt(_finite(value)))

    @staticmethod
    def floor(value: Any) -> int:
        return math.floor(_finite(value))

    @staticmethod
    def hypot(*values: Any) -> float:
        if not 2 <= len(values) <= 8:
            raise RestrictedCodeError("math hypot arguments")
        return _finite(math.hypot(*[_finite(value) for value in values]))

    @staticmethod
    def isfinite(value: Any) -> bool:
        return type(value) in (int, float) and math.isfinite(value)


class _Numbers:
    Real = (int, float)
    Integral = int


NUMBERS = _Numbers()


class _GeneratedException:
    def __init__(self, name: str):
        self.name = name


class _Linprog:
    pass


LINPROG = _Linprog()


@dataclass(frozen=True)
class _LinprogResult:
    success: bool
    fun: float | None
    x: list[float] | None
    message: str


class _Interpreter:
    def __init__(self, tree: ast.Module, data_files: dict[str, Any] | None = None,
                 *, stop_at_optimize: bool = False,
                 solve_model: Any = None):
        self.tree = tree
        self.steps = 0
        self.functions: dict[str, _Function] = {}
        self.data_files = dict(data_files or {})
        self.stop_at_optimize = stop_at_optimize
        self.solve_model = solve_model
        self.models: list[_Model] = []
        self.globals: dict[str, Any] = {
            "GRB": GRB, "gp": GP, "gurobipy": GP,
            "math": _Math(), "json": _SafeJSON(), "numbers": NUMBERS,
            "itertools": ITERTOOLS, "np": NUMPY, "numpy": NUMPY,
            "int": int, "float": float, "bool": bool, "str": str,
        }

    def tick(self, amount: int = 1) -> None:
        self.steps += amount
        if self.steps > MAX_STEPS:
            raise RestrictedCodeError("execution step limit")

    def run(self) -> dict[str, Any]:
        self._load_module()
        if "solve_problem" not in self.functions:
            raise RestrictedCodeError("solve_problem function missing")
        result = self._call_function(self.functions["solve_problem"], [], {})
        if not isinstance(result, _Model):
            raise RestrictedCodeError("solve_problem must return the model")
        return result.export()

    def _load_module(self) -> None:
        for statement in self.tree.body:
            if isinstance(statement, ast.ImportFrom):
                self._import_from(statement, self.globals)
            elif isinstance(statement, ast.Import):
                self._import(statement, self.globals)
            elif isinstance(statement, ast.FunctionDef):
                self._define(statement)
            elif isinstance(statement, ast.Assign):
                self._statement(statement, self.globals)
            elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant) \
                    and isinstance(statement.value.value, str):
                continue
            else:
                raise RestrictedCodeError("module may contain only imports and functions")

    def run_function(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._load_module()
        function = self.functions.get(name)
        if function is None:
            raise RestrictedCodeError("target function missing")
        parameters = [item.arg for item in function.node.args.args]
        default_count = len(function.node.args.defaults)
        required = set(parameters[:len(parameters) - default_count] if default_count else parameters)
        if not required <= set(arguments) or not set(arguments) <= set(parameters):
            raise RestrictedCodeError("function argument mismatch")
        try:
            result = self._call_function(function, [], arguments)
        except _ModelReady as ready:
            return ready.model.export()
        if isinstance(result, _Model):
            return result.export()
        if len(self.models) == 1 and self.models[0].optimized:
            return self.models[0].export()
        raise RestrictedCodeError("target function did not construct and optimize one model")

    def run_value_function(self, name: str, arguments: dict[str, Any]) -> Any:
        self._load_module()
        function = self.functions.get(name)
        if function is None:
            raise RestrictedCodeError("target function missing")
        parameters = [item.arg for item in function.node.args.args]
        default_count = len(function.node.args.defaults)
        required = set(parameters[:len(parameters) - default_count] if default_count else parameters)
        if not required <= set(arguments) or not set(arguments) <= set(parameters):
            raise RestrictedCodeError("function argument mismatch")
        try:
            result = self._call_function(function, [], arguments)
        except _ModelReady as exc:
            raise RestrictedCodeError("value function invoked an optimizer") from exc
        try:
            encoded = json.dumps(result, allow_nan=False)
        except (TypeError, ValueError, OverflowError) as exc:
            raise RestrictedCodeError("non-JSON function result") from exc
        if len(encoded.encode()) > MAX_CODE_BYTES:
            raise RestrictedCodeError("function result size limit")
        return json.loads(encoded)

    def run_evaluated_function(self, name: str, arguments: dict[str, Any]) -> Any:
        if self.solve_model is None:
            raise RestrictedCodeError("trusted solver callback required")
        self._load_module()
        function = self.functions.get(name)
        if function is None:
            raise RestrictedCodeError("target function missing")
        try:
            result = self._call_function(function, [], arguments)
        except _ModelReady as exc:
            raise RestrictedCodeError("unexpected optimizer boundary") from exc
        try:
            encoded = json.dumps(result, allow_nan=False)
        except (TypeError, ValueError, OverflowError) as exc:
            raise RestrictedCodeError("non-JSON function result") from exc
        if len(encoded.encode()) > MAX_CODE_BYTES:
            raise RestrictedCodeError("function result size limit")
        return json.loads(encoded)

    def _solve(self, model: _Model) -> dict[str, Any]:
        if self.solve_model is None:
            raise RestrictedCodeError("trusted solver callback required")
        result = self.solve_model({"op": "solve", "model": model.export()})
        if not isinstance(result, dict):
            raise RestrictedCodeError("trusted solver result shape")
        model.apply_solution(result)
        return result

    def _import(self, node: ast.Import, env: dict[str, Any]) -> None:
        for alias in node.names:
            if alias.name == "math" and alias.asname in {None, "math"}:
                env[alias.asname or alias.name] = self.globals["math"]
            elif alias.name == "json" and alias.asname in {None, "json"}:
                env[alias.asname or alias.name] = self.globals["json"]
            elif alias.name == "gurobipy" and alias.asname in {None, "gp", "gurobipy"}:
                env[alias.asname or alias.name] = GP
            elif alias.name == "numbers" and alias.asname in {None, "numbers"}:
                env[alias.asname or alias.name] = NUMBERS
            elif alias.name == "itertools" and alias.asname in {None, "itertools"}:
                env[alias.asname or alias.name] = ITERTOOLS
            elif alias.name == "numpy" and alias.asname in {None, "np", "numpy"}:
                env[alias.asname or alias.name] = NUMPY
            else:
                raise RestrictedCodeError("unsupported import")

    def _import_from(self, node: ast.ImportFrom, env: dict[str, Any]) -> None:
        if node.level:
            raise RestrictedCodeError("unsupported import-from")
        if node.module == "math":
            for alias in node.names:
                if alias.name not in {"isfinite", "hypot", "sqrt", "floor"} \
                        or alias.asname not in {None, alias.name}:
                    raise RestrictedCodeError("unsupported math import")
                env[alias.asname or alias.name] = getattr(self.globals["math"], alias.name)
            return
        if node.module == "itertools":
            for alias in node.names:
                if alias.name not in {"combinations", "permutations"} \
                        or alias.asname not in {None, alias.name}:
                    raise RestrictedCodeError("unsupported itertools import")
                env[alias.asname or alias.name] = _ItertoolsFunction(alias.name)
            return
        if node.module == "numbers":
            for alias in node.names:
                if alias.name not in {"Integral", "Real"} or alias.asname is not None:
                    raise RestrictedCodeError("unsupported numbers import")
                env[alias.name] = getattr(NUMBERS, alias.name)
            return
        if node.module == "scipy.optimize":
            if len(node.names) != 1 or node.names[0].name != "linprog" \
                    or node.names[0].asname not in {None, "linprog"}:
                raise RestrictedCodeError("unsupported scipy import")
            env[node.names[0].asname or "linprog"] = LINPROG
            return
        if node.module != "gurobipy":
            raise RestrictedCodeError("unsupported import-from")
        allowed = {
            "Model": self._new_model, "GRB": GRB,
            "quicksum": self._quicksum,
        }
        for alias in node.names:
            if alias.name == "*":
                env.update(allowed)
            elif alias.name in allowed and (alias.asname is None or not alias.asname.startswith("_")):
                env[alias.asname or alias.name] = allowed[alias.name]
            else:
                raise RestrictedCodeError("unsupported gurobipy import")

    def _new_model(self, *args: Any, **kwargs: Any) -> _Model:
        model = _Model(*args, **kwargs)
        self.models.append(model)
        if len(self.models) > MAX_MODELS:
            raise RestrictedCodeError("model count limit")
        return model

    def _linprog(self, args: list[Any], kwargs: dict[str, Any]) -> _Model:
        names = ("c", "A_ub", "b_ub", "A_eq", "b_eq", "bounds", "method")
        if len(args) > len(names):
            raise RestrictedCodeError("linprog argument count")
        values = dict(zip(names, args))
        for key, value in kwargs.items():
            if key not in names or key in values:
                raise RestrictedCodeError("linprog keyword")
            values[key] = value
        if values.get("method", "highs") not in {None, "highs"}:
            raise RestrictedCodeError("linprog method")
        def sequence(value: Any) -> list[Any] | None:
            if isinstance(value, _SafeArray):
                return list(value._flat)
            if isinstance(value, (list, tuple)):
                return list(value)
            return None

        objective = sequence(values.get("c"))
        if not objective:
            raise RestrictedCodeError("linprog objective")
        n = len(objective)
        bounds = values.get("bounds")
        if bounds is None:
            bounds = [(0, None)] * n
        elif isinstance(bounds, tuple) and len(bounds) == 2 \
                and all(value is None or type(value) in (int, float) for value in bounds):
            bounds = [bounds] * n
        if not isinstance(bounds, (list, tuple)) or len(bounds) != n:
            raise RestrictedCodeError("linprog bounds")
        model = self._new_model("scipy_linprog")
        variables = []
        for index, bound in enumerate(bounds):
            if not isinstance(bound, (list, tuple)) or len(bound) != 2:
                raise RestrictedCodeError("linprog bound pair")
            variables.append(model.addVar(lb=bound[0], ub=bound[1], name=f"x[{index}]"))
        model.setObjective(sum((_finite(coefficient) * variables[index]
                                for index, coefficient in enumerate(objective)), 0), GRB.MINIMIZE)

        def rows(matrix: Any, rhs: Any, sense: str) -> None:
            if matrix is None and rhs is None:
                return
            if isinstance(matrix, _SafeArray):
                matrix = matrix.tolist()
            if isinstance(rhs, _SafeArray):
                rhs = rhs.tolist()
            if not isinstance(matrix, (list, tuple)) or not isinstance(rhs, (list, tuple)) \
                    or len(matrix) != len(rhs):
                raise RestrictedCodeError("linprog row shape")
            for row, bound in zip(matrix, rhs):
                if not isinstance(row, (list, tuple)) or len(row) != n:
                    raise RestrictedCodeError("linprog row width")
                expression = sum((_finite(coefficient) * variables[index]
                                  for index, coefficient in enumerate(row)), 0)
                model.addConstr({"eq": expression == bound, "le": expression <= bound}[sense])
        rows(values.get("A_ub"), values.get("b_ub"), "le")
        rows(values.get("A_eq"), values.get("b_eq"), "eq")
        model.optimize()
        return model

    @staticmethod
    def _quicksum(values: Any) -> Any:
        return sum(values, 0)

    def _define(self, node: ast.FunctionDef) -> None:
        if node.decorator_list or node.name.startswith("_") or node.args.vararg or node.args.kwarg \
                or node.args.kwonlyargs or node.args.kw_defaults:
            raise RestrictedCodeError("unsupported function signature")
        if node.name in self.functions:
            raise RestrictedCodeError("duplicate function")
        self.functions[node.name] = _Function(node)

    def _call_function(self, function: _Function, args: list[Any], kwargs: dict[str, Any]) -> Any:
        parameters = [item.arg for item in function.node.args.args]
        if len(args) > len(parameters) or any(key not in parameters for key in kwargs):
            raise RestrictedCodeError("function argument mismatch")
        env = _Environment(function.closure or {}, function.nonlocal_names)
        bound = dict(zip(parameters, args))
        for key, value in kwargs.items():
            if key in bound:
                raise RestrictedCodeError("function argument mismatch")
            bound[key] = value
        default_count = len(function.node.args.defaults)
        default_names = parameters[len(parameters) - default_count:] if default_count else []
        default_env = dict(env)
        default_env.update(bound)
        for key, node in zip(default_names, function.node.args.defaults):
            if key not in bound:
                bound[key] = self._expression(node, default_env)
        if set(bound) != set(parameters):
            raise RestrictedCodeError("function argument mismatch")
        env.update(bound)
        try:
            self._block(function.node.body, env)
        except _Return as result:
            return result.value
        return None

    def _block(self, statements: list[ast.stmt], env: dict[str, Any]) -> None:
        for statement in statements:
            self.tick()
            self._statement(statement, env)

    def _statement(self, node: ast.stmt, env: dict[str, Any]) -> None:
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise RestrictedCodeError("multiple assignment targets unsupported")
            self._store(node.targets[0], self._expression(node.value, env), env)
        elif isinstance(node, ast.AugAssign):
            old = self._expression(node.target, env)
            value = self._binary(node.op, old, self._expression(node.value, env))
            self._store(node.target, value, env)
        elif isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return
            self._expression(node.value, env)
        elif isinstance(node, ast.For):
            values = list(self._expression(node.iter, env))
            if len(values) > MAX_RANGE:
                raise RestrictedCodeError("loop iteration limit")
            for value in values:
                self.tick()
                self._store(node.target, value, env)
                try:
                    self._block(node.body, env)
                except _Continue:
                    continue
                except _Break:
                    break
            else:
                self._block(node.orelse, env)
        elif isinstance(node, ast.While):
            count = 0
            while self._truth(self._expression(node.test, env)):
                count += 1
                self.tick()
                if count > MAX_RANGE:
                    raise RestrictedCodeError("while iteration limit")
                try:
                    self._block(node.body, env)
                except _Continue:
                    continue
                except _Break:
                    break
            else:
                self._block(node.orelse, env)
        elif isinstance(node, ast.If):
            self._block(node.body if self._truth(self._expression(node.test, env)) else node.orelse, env)
        elif isinstance(node, ast.With):
            if len(node.items) != 1 or node.items[0].optional_vars is None:
                raise RestrictedCodeError("unsupported with statement")
            value = self._expression(node.items[0].context_expr, env)
            if not isinstance(value, _SafeFile):
                raise RestrictedCodeError("with requires an injected data handle")
            self._store(node.items[0].optional_vars, value, env)
            self._block(node.body, env)
        elif isinstance(node, ast.Import):
            self._import(node, env)
        elif isinstance(node, ast.ImportFrom):
            self._import_from(node, env)
        elif isinstance(node, ast.Try):
            # Native CoE functions often wrap the complete model build in a
            # broad solver try/except.  Generated code is not actually run and
            # no external Gurobi exception can occur, so only the guarded model
            # construction path is interpreted.  Any adapter error still fails
            # closed rather than being swallowed by the author handler.
            self._block(node.body, env)
        elif isinstance(node, ast.FunctionDef):
            if node.decorator_list or node.name.startswith("_") or node.args.vararg or node.args.kwarg \
                    or node.args.kwonlyargs or node.args.kw_defaults:
                raise RestrictedCodeError("unsupported local function signature")
            names = tuple(name for statement in node.body if isinstance(statement, ast.Nonlocal)
                          for name in statement.names)
            if any(name.startswith("_") or name not in env for name in names):
                raise RestrictedCodeError("invalid nonlocal binding")
            function = _Function(node, env, names)
            env[node.name] = function
        elif isinstance(node, ast.Nonlocal):
            if not isinstance(env, _Environment) \
                    or any(name.startswith("_") or name not in env.nonlocal_names
                           for name in node.names):
                raise RestrictedCodeError("invalid nonlocal declaration")
        elif isinstance(node, ast.Raise):
            value = None if node.exc is None else self._expression(node.exc, env)
            if value is not None and not isinstance(value, _GeneratedException):
                raise RestrictedCodeError("unsupported generated exception")
            raise RestrictedCodeError("generated_validation_error")
        elif isinstance(node, ast.Return):
            raise _Return(None if node.value is None else self._expression(node.value, env))
        elif isinstance(node, ast.Break):
            raise _Break()
        elif isinstance(node, ast.Continue):
            raise _Continue()
        else:
            raise RestrictedCodeError(f"unsupported statement: {type(node).__name__}")

    def _lookup(self, name: str, env: dict[str, Any]) -> Any:
        if name.startswith("_") and name != "_":
            raise RestrictedCodeError("private names forbidden")
        if isinstance(env, _Environment) and name in env.nonlocal_names:
            return env.nonlocal_source[name]
        if name in env:
            return env[name]
        if name in self.globals:
            return self.globals[name]
        if name in self.functions:
            return self.functions[name]
        raise RestrictedCodeError(f"unknown name: {name}")

    def _expression(self, node: ast.expr, env: dict[str, Any]) -> Any:
        self.tick()
        if isinstance(node, ast.Constant):
            if type(node.value) not in (int, float, str, bool, type(None)):
                raise RestrictedCodeError("unsupported constant")
            if isinstance(node.value, str) and len(node.value) > 10_000:
                raise RestrictedCodeError("string limit")
            return node.value
        if isinstance(node, ast.Name):
            return self._lookup(node.id, env)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            values = []
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    values.extend(list(self._expression(item.value, env)))
                else:
                    values.append(self._expression(item, env))
                if len(values) > MAX_COLLECTION:
                    raise RestrictedCodeError("collection limit")
            if isinstance(node, ast.Tuple):
                return tuple(values)
            if isinstance(node, ast.Set):
                return set(values)
            return values
        if isinstance(node, ast.Dict):
            if len(node.keys) > MAX_COLLECTION or any(key is None for key in node.keys):
                raise RestrictedCodeError("dictionary limit")
            return {self._expression(k, env): self._expression(v, env)
                    for k, v in zip(node.keys, node.values)}
        if isinstance(node, ast.BinOp):
            return self._binary(node.op, self._expression(node.left, env), self._expression(node.right, env))
        if isinstance(node, ast.UnaryOp):
            value = self._expression(node.operand, env)
            if isinstance(node.op, ast.USub):
                return -value
            if isinstance(node.op, ast.UAdd):
                return value
            if isinstance(node.op, ast.Not):
                return not self._truth(value)
            raise RestrictedCodeError("unsupported unary operator")
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Slice):
                def bound(value: ast.expr | None) -> int | None:
                    return None if value is None else int(_finite(self._expression(value, env)))
                key = slice(bound(node.slice.lower), bound(node.slice.upper), bound(node.slice.step))
            else:
                key = self._expression(node.slice, env)
            return self._expression(node.value, env)[key]
        if isinstance(node, ast.Compare):
            left = self._expression(node.left, env)
            if len(node.ops) != len(node.comparators):
                raise RestrictedCodeError("invalid comparison")
            values = []
            for operator, comparator in zip(node.ops, node.comparators):
                right = self._expression(comparator, env)
                value = self._compare(operator, left, right)
                values.append(value)
                left = right
            if len(values) == 1:
                return values[0]
            if any(isinstance(value, (_Expr, _Constraint)) for value in values):
                raise RestrictedCodeError("symbolic chained comparison")
            return all(self._truth(value) for value in values)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for item in node.values:
                    if not self._truth(self._expression(item, env)):
                        return False
                return True
            if isinstance(node.op, ast.Or):
                for item in node.values:
                    if self._truth(self._expression(item, env)):
                        return True
                return False
            raise RestrictedCodeError("unsupported boolean operator")
        if isinstance(node, ast.IfExp):
            return self._expression(node.body if self._truth(self._expression(node.test, env))
                                    else node.orelse, env)
        if isinstance(node, ast.JoinedStr):
            chunks = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    chunks.append(str(value.value))
                elif isinstance(value, ast.FormattedValue):
                    if value.format_spec is not None or value.conversion not in {-1, 115}:
                        raise RestrictedCodeError("format operation unsupported")
                    chunks.append(str(self._expression(value.value, env)))
                else:
                    raise RestrictedCodeError("f-string part unsupported")
            result = "".join(chunks)
            if len(result) > 10_000:
                raise RestrictedCodeError("string limit")
            return result
        if isinstance(node, ast.Call):
            return self._call(node, env)
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.DictComp, ast.SetComp)):
            return self._comprehension(node, env)
        if isinstance(node, ast.Lambda):
            if node.args.vararg or node.args.kwarg or node.args.kwonlyargs \
                    or node.args.kw_defaults or node.args.defaults:
                raise RestrictedCodeError("unsupported lambda signature")
            return _Lambda(node, dict(env))
        if isinstance(node, ast.Attribute):
            return self._attribute(self._expression(node.value, env), node.attr)
        raise RestrictedCodeError(f"unsupported expression: {type(node).__name__}")

    def _collection(self, values: list[Any]) -> list[Any]:
        if len(values) > MAX_COLLECTION:
            raise RestrictedCodeError("collection limit")
        return values

    def _binary(self, operator: ast.operator, left: Any, right: Any) -> Any:
        try:
            if isinstance(operator, ast.Add):
                value = left + right
            elif isinstance(operator, ast.Sub):
                value = left - right
            elif isinstance(operator, ast.Mult):
                value = left * right
            elif isinstance(operator, ast.Div):
                value = left / right
            elif isinstance(operator, ast.Pow):
                if isinstance(left, _Expr) or isinstance(right, _Expr):
                    raise RestrictedCodeError("nonlinear power")
                value = _finite(left) ** _finite(right)
            elif isinstance(operator, ast.Mod):
                if isinstance(left, _Expr) or isinstance(right, _Expr):
                    raise RestrictedCodeError("symbolic modulo")
                if isinstance(left, str):
                    allowed = (str, int, float)
                    parts = right if isinstance(right, tuple) else (right,)
                    if not all(type(part) in allowed for part in parts):
                        raise RestrictedCodeError("string formatting values")
                    value = left % right
                    if len(value) > 10_000:
                        raise RestrictedCodeError("string limit")
                else:
                    value = _finite(left) % _finite(right)
            elif isinstance(operator, ast.BitOr):
                if isinstance(left, set) and isinstance(right, set):
                    value = left | right
                    if len(value) > MAX_COLLECTION:
                        raise RestrictedCodeError("set limit")
                elif type(left) is int and type(right) is int:
                    value = left | right
                else:
                    raise RestrictedCodeError("bitwise-or operands")
            elif isinstance(operator, (ast.BitAnd, ast.BitXor, ast.LShift)):
                if type(left) is not int or type(right) is not int:
                    raise RestrictedCodeError("integer bitwise operands")
                if isinstance(operator, ast.BitAnd):
                    value = left & right
                elif isinstance(operator, ast.BitXor):
                    value = left ^ right
                else:
                    if not 0 <= right <= 40:
                        raise RestrictedCodeError("left-shift limit")
                    value = left << right
            else:
                raise RestrictedCodeError("unsupported binary operator")
        except (ArithmeticError, TypeError, OverflowError) as exc:
            raise RestrictedCodeError("invalid arithmetic") from exc
        if type(value) in (int, float):
            _finite(value)
        return value

    def _compare(self, operator: ast.cmpop, left: Any, right: Any) -> Any:
        if isinstance(operator, ast.LtE):
            return left <= right
        if isinstance(operator, ast.GtE):
            return left >= right
        if isinstance(operator, ast.Eq):
            return left == right
        if isinstance(operator, ast.NotEq):
            return left != right
        if isinstance(operator, ast.Lt):
            return left < right
        if isinstance(operator, ast.Gt):
            return left > right
        if isinstance(operator, ast.In):
            return left in right
        if isinstance(operator, ast.NotIn):
            return left not in right
        if isinstance(operator, ast.IsNot):
            return left is not right
        if isinstance(operator, ast.Is):
            return left is right
        raise RestrictedCodeError("unsupported comparison")

    def _truth(self, value: Any) -> bool:
        if isinstance(value, (_Expr, _Constraint, _Model, _Function, _Lambda)):
            raise RestrictedCodeError("symbolic object cannot be a condition")
        return bool(value)

    def _attribute(self, value: Any, name: str) -> Any:
        if name.startswith("_"):
            raise RestrictedCodeError("private attribute forbidden")
        if value is GRB and name in {
            "CONTINUOUS", "INTEGER", "BINARY", "MINIMIZE", "MAXIMIZE", "INFINITY", "OPTIMAL",
            "INFEASIBLE", "INF_OR_UNBD", "UNBOUNDED",
        }:
            return getattr(value, name)
        if value is GP and name in {"Model", "quicksum", "GRB"}:
            return {"Model": self._new_model, "quicksum": self._quicksum, "GRB": GRB}[name]
        if isinstance(value, _Math) and name in {"sqrt", "floor", "hypot", "inf"}:
            return getattr(value, name)
        if isinstance(value, _Math) and name == "isfinite":
            return value.isfinite
        if value is ITERTOOLS and name in {"combinations", "permutations"}:
            return _ItertoolsFunction(name)
        if value is NUMPY and name in {"array", "zeros"}:
            return name
        if value is NUMBERS and name in {"Real", "Integral"}:
            return getattr(value, name)
        if isinstance(value, _SafeJSON) and name == "load":
            return value.load
        if isinstance(value, _Var) and name in {"ub", "X", "x"}:
            return getattr(value, name)
        if isinstance(value, _Model) and name in {
            "Params", "ModelSense", "Status", "status", "ObjVal", "objVal", "SolCount",
        }:
            return getattr(value, name)
        if isinstance(value, _LinprogResult) and name in {"success", "fun", "x", "message"}:
            return getattr(value, name)
        if isinstance(value, _SafeArray) and name in {"shape", "size"}:
            return getattr(value, name)
        raise RestrictedCodeError("unsupported attribute")

    def _call_lambda(self, function: _Lambda, args: list[Any], kwargs: dict[str, Any]) -> Any:
        parameters = [item.arg for item in function.node.args.args]
        if kwargs or len(args) != len(parameters):
            raise RestrictedCodeError("lambda argument mismatch")
        env = dict(function.closure)
        env.update(zip(parameters, args))
        return self._expression(function.node.body, env)

    def _call_key(self, function: Any, value: Any) -> Any:
        if not isinstance(function, _Lambda):
            raise RestrictedCodeError("key must be a bounded lambda")
        return self._call_lambda(function, [value], {})

    def _itertools(self, name: str, args: list[Any], kwargs: dict[str, Any]) -> list[Any]:
        if kwargs or not 1 <= len(args) <= 2:
            raise RestrictedCodeError("itertools arguments")
        values = list(args[0])
        if len(values) > MAX_RANGE:
            raise RestrictedCodeError("itertools input limit")
        size = int(_finite(args[1])) if len(args) == 2 else len(values)
        if not 0 <= size <= len(values):
            return []
        count = math.comb(len(values), size) if name == "combinations" \
            else math.factorial(len(values)) // math.factorial(len(values) - size)
        if count > MAX_COLLECTION:
            raise RestrictedCodeError("itertools output limit")
        source = itertools.combinations(values, size) if name == "combinations" \
            else itertools.permutations(values, size)
        return list(source)

    def _call(self, node: ast.Call, env: dict[str, Any]) -> Any:
        args = [self._expression(x, env) for x in node.args]
        kwargs = {}
        for item in node.keywords:
            if item.arg is None or item.arg in kwargs:
                raise RestrictedCodeError("invalid keyword arguments")
            kwargs[item.arg] = self._expression(item.value, env)
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name == "Model":
                return self._new_model(*args, **kwargs)
            if name == "quicksum":
                if kwargs or len(args) != 1:
                    raise RestrictedCodeError("quicksum arguments")
                return self._quicksum(args[0])
            candidate = env.get(name, self.globals.get(name, self.functions.get(name)))
            if isinstance(candidate, _Function):
                return self._call_function(candidate, args, kwargs)
            if isinstance(candidate, _Lambda):
                return self._call_lambda(candidate, args, kwargs)
            if isinstance(candidate, _ItertoolsFunction):
                return self._itertools(candidate.name, args, kwargs)
            if candidate is LINPROG:
                model = self._linprog(args, kwargs)
                if self.stop_at_optimize:
                    raise _ModelReady(model)
                if self.solve_model is not None:
                    solved = self._solve(model)
                    point = solved.get("point")
                    return _LinprogResult(
                        success=solved.get("status") == "optimal",
                        fun=solved.get("objective"),
                        x=_SafeArray(
                            [point[variable.identifier] for variable in model.variables],
                            (len(model.variables),),
                        ) if isinstance(point, dict) else None,
                        message=str(solved.get("reason") or solved.get("status") or ""),
                    )
                return model
            if callable(candidate) and candidate == self.globals["math"].isfinite:
                if kwargs or len(args) != 1:
                    raise RestrictedCodeError("isfinite arguments")
                return candidate(args[0])
            if name in {"sqrt", "floor", "hypot", "isfinite"} \
                    and candidate == getattr(self.globals["math"], name):
                if kwargs:
                    raise RestrictedCodeError("math keywords unsupported")
                return candidate(*args)
            if callable(candidate) and (
                candidate == self._new_model or candidate == self._quicksum
            ):
                return candidate(*args, **kwargs)
            return self._builtin(name, args, kwargs)
        if isinstance(node.func, ast.Attribute):
            receiver = self._expression(node.func.value, env)
            return self._method(receiver, node.func.attr, args, kwargs)
        raise RestrictedCodeError("unsupported call target")

    def _builtin(self, name: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        if name == "range":
            if kwargs:
                raise RestrictedCodeError("range keywords unsupported")
            values = range(*[int(_finite(x)) for x in args])
            if len(values) > MAX_RANGE:
                raise RestrictedCodeError("range limit")
            return values
        if name == "open" and 1 <= len(args) <= 2:
            if kwargs:
                raise RestrictedCodeError("open keywords unsupported")
            path = str(args[0])
            mode = str(args[1]) if len(args) == 2 else "r"
            if mode not in {"r", "rt"} or path not in self.data_files:
                raise RestrictedCodeError("file path is not an injected read-only input")
            return _SafeFile(self.data_files[path])
        if name == "len" and len(args) == 1 and not kwargs:
            return len(args[0])
        if name == "dict" and len(args) <= 1 and not kwargs:
            value = dict(args[0]) if args else {}
            if len(value) > MAX_COLLECTION:
                raise RestrictedCodeError("dictionary limit")
            return value
        if name == "tuple" and len(args) <= 1 and not kwargs:
            value = tuple(args[0]) if args else ()
            if len(value) > MAX_COLLECTION:
                raise RestrictedCodeError("tuple limit")
            return value
        if name == "int" and len(args) == 1 and not kwargs:
            return int(_finite(args[0]))
        if name == "str" and len(args) == 1 and not kwargs:
            value = str(args[0])
            if len(value) > 10_000:
                raise RestrictedCodeError("string limit")
            return value
        if name == "float" and len(args) == 1 and not kwargs:
            return _finite(args[0])
        if name == "round" and 1 <= len(args) <= 2 and not kwargs:
            return round(_finite(args[0]), int(_finite(args[1]))) if len(args) == 2 else round(_finite(args[0]))
        if name == "isinstance" and len(args) == 2 and not kwargs:
            allowed_types = {int, float, bool, str, list, tuple}
            specification = args[1] if isinstance(args[1], tuple) else (args[1],)
            if not specification or any(item not in allowed_types for item in specification):
                raise RestrictedCodeError("isinstance type")
            return isinstance(args[0], specification)
        if name == "zip" and args and not kwargs:
            values = list(zip(*args))
            return self._collection(values)
        if name == "abs" and len(args) == 1 and not kwargs:
            if isinstance(args[0], _Expr):
                raise RestrictedCodeError("symbolic abs")
            return abs(_finite(args[0]))
        if name in {"ValueError", "TypeError", "RuntimeError"} and len(args) <= 1 and not kwargs:
            return _GeneratedException(name)
        if name == "enumerate" and 1 <= len(args) <= 2 and set(kwargs) <= {"start"}:
            if len(args) == 2 and "start" in kwargs:
                raise RestrictedCodeError("enumerate start duplicated")
            start_value = kwargs.get("start", args[1] if len(args) == 2 else 0)
            start = int(_finite(start_value))
            return self._collection(list(enumerate(args[0], start)))
        if name == "list" and len(args) <= 1 and not kwargs:
            return self._collection(list(args[0]) if args else [])
        if name == "set" and len(args) <= 1 and not kwargs:
            value = set(args[0]) if args else set()
            if len(value) > MAX_COLLECTION:
                raise RestrictedCodeError("set limit")
            return value
        if name == "sum" and 1 <= len(args) <= 2 and not kwargs:
            return sum(args[0], args[1] if len(args) == 2 else 0)
        if name == "any" and len(args) == 1 and not kwargs:
            return any(self._truth(value) for value in args[0])
        if name == "all" and len(args) == 1 and not kwargs:
            return all(self._truth(value) for value in args[0])
        if name == "next" and 1 <= len(args) <= 2 and not kwargs:
            iterator = iter(args[0])
            try:
                return next(iterator)
            except StopIteration:
                if len(args) == 2:
                    return args[1]
                raise RestrictedCodeError("next on empty iterable") from None
        if name == "sorted" and len(args) == 1 and set(kwargs) <= {"key", "reverse"}:
            values = list(args[0])
            if len(values) > MAX_COLLECTION:
                raise RestrictedCodeError("sorted limit")
            key = kwargs.get("key")
            reverse = kwargs.get("reverse", False)
            if type(reverse) is not bool:
                raise RestrictedCodeError("sorted reverse")
            return sorted(values, key=(lambda value: self._call_key(key, value)) if key is not None else None,
                          reverse=reverse)
        if name == "max" and args:
            if set(kwargs) - {"default", "key"} or kwargs and len(args) != 1:
                raise RestrictedCodeError("max keywords unsupported")
            if len(args) == 1:
                values = list(args[0])
                if len(values) > MAX_COLLECTION:
                    raise RestrictedCodeError("max limit")
                options = {}
                if "default" in kwargs:
                    options["default"] = kwargs["default"]
                if "key" in kwargs:
                    options["key"] = lambda value: self._call_key(kwargs["key"], value)
                return max(values, **options)
            return max(args)
        if name == "min" and args:
            if set(kwargs) - {"default", "key"} or kwargs and len(args) != 1:
                raise RestrictedCodeError("min keywords unsupported")
            if len(args) == 1:
                values = list(args[0])
                if len(values) > MAX_COLLECTION:
                    raise RestrictedCodeError("min limit")
                options = {}
                if "default" in kwargs:
                    options["default"] = kwargs["default"]
                if "key" in kwargs:
                    options["key"] = lambda value: self._call_key(kwargs["key"], value)
                return min(values, **options)
            return min(args)
        if kwargs:
            raise RestrictedCodeError("builtin keywords unsupported")
        raise RestrictedCodeError(f"unsupported builtin: {name}")

    def _method(self, receiver: Any, name: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        if name.startswith("_"):
            raise RestrictedCodeError("private method forbidden")
        if receiver is GP and name in {"Model", "quicksum"}:
            return self._new_model(*args, **kwargs) if name == "Model" else self._quicksum(*args, **kwargs)
        if receiver is ITERTOOLS and name in {"combinations", "permutations"}:
            return self._itertools(name, args, kwargs)
        if receiver is NUMPY and name in {"array", "zeros"}:
            if name == "array":
                if not 1 <= len(args) <= 2 or set(kwargs) - {"dtype"}:
                    raise RestrictedCodeError("numpy array arguments")
                dtype = kwargs.get("dtype", args[1] if len(args) == 2 else None)
                if dtype not in {None, float, int}:
                    raise RestrictedCodeError("numpy dtype")
                array = _SafeArray(args[0])
                if dtype is not None:
                    array = _SafeArray([dtype(_finite(value)) for value in array._flat], array.shape)
                return array
            if len(args) != 1 or kwargs:
                raise RestrictedCodeError("numpy zeros arguments")
            shape = tuple(args[0]) if isinstance(args[0], (list, tuple)) else (int(_finite(args[0])),)
            shape = tuple(int(_finite(value)) for value in shape)
            if not shape or math.prod(shape) > MAX_COLLECTION:
                raise RestrictedCodeError("numpy zeros size")
            return _SafeArray([0.0] * math.prod(shape), shape)
        if isinstance(receiver, _Model) and name in {"addVar", "addVars", "addConstr", "addConstrs", "setObjective", "setParam", "optimize", "update", "dispose"}:
            result = getattr(receiver, name)(*args, **kwargs)
            if name == "optimize" and self.stop_at_optimize:
                raise _ModelReady(receiver)
            if name == "optimize" and self.solve_model is not None:
                self._solve(receiver)
            return result
        if isinstance(receiver, _Math) and name in {"sqrt", "floor", "hypot", "isfinite"}:
            if kwargs:
                raise RestrictedCodeError("math keywords unsupported")
            return getattr(receiver, name)(*args)
        if isinstance(receiver, _SafeJSON) and name == "load" and len(args) == 1 and not kwargs:
            return receiver.load(args[0])
        if isinstance(receiver, list) and name in {"append", "pop"} and not kwargs:
            if name == "append" and len(args) == 1:
                if len(receiver) >= MAX_COLLECTION:
                    raise RestrictedCodeError("list limit")
                return receiver.append(args[0])
            if name == "pop" and not args:
                return receiver.pop()
        if isinstance(receiver, list) and name == "sort" and set(kwargs) <= {"key", "reverse"} and not args:
            key = kwargs.get("key")
            reverse = kwargs.get("reverse", False)
            if type(reverse) is not bool:
                raise RestrictedCodeError("sort reverse")
            receiver.sort(key=(lambda value: self._call_key(key, value)) if key is not None else None,
                          reverse=reverse)
            return None
        if isinstance(receiver, set) and name in {"add", "pop"} and not kwargs:
            if name == "add" and len(args) == 1:
                if len(receiver) >= MAX_COLLECTION:
                    raise RestrictedCodeError("set limit")
                return receiver.add(args[0])
            if name == "pop" and not args:
                return receiver.pop()
        if isinstance(receiver, dict) and not kwargs:
            if name == "items" and not args:
                return list(receiver.items())
            if name == "values" and not args:
                return list(receiver.values())
            if name == "keys" and not args:
                return list(receiver.keys())
            if name == "get" and 1 <= len(args) <= 2:
                return receiver.get(args[0], args[1] if len(args) == 2 else None)
            if name == "sum":
                if not args:
                    return sum(receiver.values(), 0)
                selected = []
                for key, value in receiver.items():
                    parts = key if isinstance(key, tuple) else (key,)
                    if len(parts) == len(args) and all(pattern == "*" or pattern == part
                                                       for pattern, part in zip(args, parts)):
                        selected.append(value)
                return sum(selected, 0)
        if isinstance(receiver, _SafeArray) and name in {"ravel", "reshape"} and not kwargs:
            if name == "ravel" and not args:
                return receiver.ravel()
            if name == "reshape" and len(args) == 1:
                return receiver.reshape(args[0])
        if isinstance(receiver, str) and name == "format" and not kwargs:
            if not all(type(value) in (str, int, float, bool, type(None)) for value in args):
                raise RestrictedCodeError("string format values")
            value = receiver.format(*args)
            if len(value) > 10_000:
                raise RestrictedCodeError("string limit")
            return value
        raise RestrictedCodeError(f"unsupported method: {name}")

    def _store(self, target: ast.expr, value: Any, env: dict[str, Any]) -> None:
        if isinstance(target, ast.Name):
            if target.id.startswith("_") and target.id != "_":
                raise RestrictedCodeError("private names forbidden")
            if isinstance(env, _Environment) and target.id in env.nonlocal_names:
                env.nonlocal_source[target.id] = value
            else:
                env[target.id] = value
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            values = list(value)
            if len(values) != len(target.elts):
                raise RestrictedCodeError("unpack mismatch")
            for item, part in zip(target.elts, values):
                self._store(item, part, env)
            return
        if isinstance(target, ast.Subscript):
            container = self._expression(target.value, env)
            def key_part(node: ast.expr) -> Any:
                if isinstance(node, ast.Slice):
                    def bound(part: ast.expr | None) -> int | None:
                        return None if part is None else int(_finite(self._expression(part, env)))
                    return slice(bound(node.lower), bound(node.upper), bound(node.step))
                if isinstance(node, ast.Tuple):
                    return tuple(key_part(item) for item in node.elts)
                return self._expression(node, env)
            key = key_part(target.slice)
            if not isinstance(container, (dict, list, _SafeArray)):
                raise RestrictedCodeError("subscript assignment target")
            if isinstance(container, dict) and key not in container and len(container) >= MAX_COLLECTION:
                raise RestrictedCodeError("dictionary limit")
            container[key] = value
            return
        if isinstance(target, ast.Attribute):
            receiver = self._expression(target.value, env)
            if isinstance(receiver, _Var) and target.attr == "ub":
                receiver.ub = value
                return
            if isinstance(receiver, _Params):
                setattr(receiver, target.attr, value)
                return
            if isinstance(receiver, _Model) and target.attr == "ModelSense":
                receiver.ModelSense = value
                return
        raise RestrictedCodeError("unsupported assignment target")

    def _comprehension(self, node: ast.expr, env: dict[str, Any]) -> Any:
        generators = node.generators  # type: ignore[attr-defined]
        values: list[Any] = []
        mapping: dict[Any, Any] = {}

        def visit(index: int, local: dict[str, Any]) -> None:
            if index == len(generators):
                self.tick()
                if isinstance(node, ast.DictComp):
                    key = self._expression(node.key, local)
                    mapping[key] = self._expression(node.value, local)
                    if len(mapping) > MAX_COLLECTION:
                        raise RestrictedCodeError("comprehension limit")
                else:
                    values.append(self._expression(node.elt, local))  # type: ignore[attr-defined]
                    if len(values) > MAX_COLLECTION:
                        raise RestrictedCodeError("comprehension limit")
                return
            generator = generators[index]
            if generator.is_async:
                raise RestrictedCodeError("async comprehension forbidden")
            iterable = list(self._expression(generator.iter, local))
            if len(iterable) > MAX_RANGE:
                raise RestrictedCodeError("comprehension range limit")
            for item in iterable:
                child = dict(local)
                self._store(generator.target, item, child)
                if all(self._truth(self._expression(test, child)) for test in generator.ifs):
                    visit(index + 1, child)

        visit(0, dict(env))
        if isinstance(node, ast.DictComp):
            return mapping
        if isinstance(node, ast.SetComp):
            return set(values)
        return values


def _code_block(text: str) -> str:
    if not isinstance(text, str) or len(text.encode()) > MAX_CODE_BYTES:
        raise RestrictedCodeError("code size limit")
    blocks = re.findall(r"```(?:python|py|gurobi)?\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (blocks[-1] if blocks else text).strip()


def compile_gurobi_source(text: str, *, data_files: dict[str, Any] | None = None) -> dict[str, Any]:
    """Interpret an allowed source program and return validated ``milp-v1``."""
    code = _code_block(text)
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise RestrictedCodeError("invalid Python syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise RestrictedCodeError("AST node limit")
    return _Interpreter(tree, data_files=data_files).run()


def compile_gurobi_function_source(text: str, function_name: str,
                                   arguments: dict[str, Any]) -> dict[str, Any]:
    """Compile a CoE-style parameterized function without executing Python.

    Interpretation stops at the function's first optimizer call, before any
    solution-value access or return post-processing.  The resulting symbolic
    model can then be solved by a trusted backend and compared with the public
    sample output.
    """
    if not isinstance(function_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", function_name):
        raise RestrictedCodeError("invalid target function name")
    try:
        detached = json.loads(json.dumps(arguments, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise RestrictedCodeError("invalid function arguments") from exc
    if not isinstance(detached, dict) or any(not isinstance(key, str) for key in detached):
        raise RestrictedCodeError("function arguments object required")
    code = _code_block(text)
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise RestrictedCodeError("invalid Python syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise RestrictedCodeError("AST node limit")
    return _Interpreter(tree, stop_at_optimize=True).run_function(function_name, detached)


def evaluate_restricted_function_source(text: str, function_name: str,
                                        arguments: dict[str, Any]) -> Any:
    """Evaluate a bounded pure-Python CoE function in the whitelist interpreter."""
    if not isinstance(function_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", function_name):
        raise RestrictedCodeError("invalid target function name")
    try:
        detached = json.loads(json.dumps(arguments, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise RestrictedCodeError("invalid function arguments") from exc
    if not isinstance(detached, dict) or any(not isinstance(key, str) for key in detached):
        raise RestrictedCodeError("function arguments object required")
    code = _code_block(text)
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise RestrictedCodeError("invalid Python syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise RestrictedCodeError("AST node limit")
    return _Interpreter(tree, stop_at_optimize=True).run_value_function(function_name, detached)


def evaluate_optimization_function_source(text: str, function_name: str,
                                          arguments: dict[str, Any], solver: Any) -> Any:
    """Interpret a CoE function and delegate only validated models to ``solver``.

    This reproduces post-solve return logic (including wrong return shapes)
    without importing the generated module.  Solver status, objective, and
    primal values are exposed only through a small Gurobi/SciPy result facade.
    """
    if not callable(solver):
        raise RestrictedCodeError("trusted solver callback required")
    if not isinstance(function_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}", function_name):
        raise RestrictedCodeError("invalid target function name")
    try:
        detached = json.loads(json.dumps(arguments, allow_nan=False))
    except (TypeError, ValueError, OverflowError) as exc:
        raise RestrictedCodeError("invalid function arguments") from exc
    if not isinstance(detached, dict) or any(not isinstance(key, str) for key in detached):
        raise RestrictedCodeError("function arguments object required")
    code = _code_block(text)
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise RestrictedCodeError("invalid Python syntax") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise RestrictedCodeError("AST node limit")
    return _Interpreter(tree, solve_model=solver).run_evaluated_function(function_name, detached)


__all__ = [
    "GRB", "RestrictedCodeError", "compile_gurobi_function_source", "compile_gurobi_source",
    "evaluate_optimization_function_source", "evaluate_restricted_function_source",
]
