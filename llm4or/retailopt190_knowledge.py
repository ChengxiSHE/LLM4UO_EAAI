"""Sparse, typed RetailOpt knowledge cards and short-decision contracts.

The cards contain public benchmark semantics and synthetic counterexamples only.
They contain no benchmark instance, objective, response or evaluator value.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping


class RetailKnowledgeError(ValueError):
    pass


@dataclass(frozen=True)
class Question:
    question_id: str
    prompt: str
    choices: tuple[str, ...]
    correct: str

    def __post_init__(self) -> None:
        if not self.question_id or len(self.choices) < 2 or self.correct not in self.choices:
            raise RetailKnowledgeError("invalid_question")
        if len(set(self.choices)) != len(self.choices):
            raise RetailKnowledgeError("duplicate_choice")


@dataclass(frozen=True)
class SkillCard:
    skill_id: str
    title: str
    questions: tuple[Question, ...]
    obligation: str
    counterexample_witness: str

    def __post_init__(self) -> None:
        if not self.skill_id or not self.questions or not self.obligation or not self.counterexample_witness:
            raise RetailKnowledgeError("invalid_skill")


CORE = SkillCard(
    skill_id="retail.core.flow.v1",
    title="Perishable inventory and objective accounting",
    questions=(
        Question("fresh_inflow", "What may enter the freshest remaining-life bucket?", ("arrivals_net_transshipment_lagged_returns_only", "arrivals_plus_prior_inventory", "arrivals_minus_current_sales"), "arrivals_net_transshipment_lagged_returns_only"),
        Question("aging", "How does a fresher bucket become the next period's older bucket?", ("shift_after_sales_from_fresher_bucket", "shift_before_sales", "copy_same_bucket_after_sales"), "shift_after_sales_from_fresher_bucket"),
        Question("waste", "Which quantity becomes expiry waste?", ("oldest_bucket_residual_after_sales", "all_unsold_inventory", "lost_sales"), "oldest_bucket_residual_after_sales"),
        Question("production_capacity", "Which flow consumes product-period procurement capacity?", ("delivered_inflow_aggregated_over_locations", "orders_placed_same_period", "sales"), "delivered_inflow_aggregated_over_locations"),
        Question("holding_cost", "Which stock is charged holding cost?", ("post_sales_nonexpiring_inventory", "all_start_inventory", "fresh_arrivals"), "post_sales_nonexpiring_inventory"),
        Question("demand_balance", "How are sales, lost sales and substitution reconciled?", ("sales_plus_lost_equals_original_plus_inbound_minus_outbound", "sales_plus_lost_equals_original", "sales_equals_original_plus_outbound"), "sales_plus_lost_equals_original_plus_inbound_minus_outbound"),
        Question("purchase_cost", "On which quantity is purchasing cost charged?", ("orders_placed", "delivered_arrivals", "sales"), "orders_placed"),
    ),
    obligation=(
        "Use start-of-period inventory indexed by remaining life. New supply enters only the freshest bucket; "
        "aging removes the sales made from the bucket being shifted; only the oldest residual expires. "
        "Capacity applies to delivered inflow, while purchasing cost applies to orders. Holding cost applies "
        "to post-sales nonexpiring inventory. Demand conservation includes substitution inflow and outflow."
    ),
    counterexample_witness=(
        "Witness: with two life buckets, one unit in the fresher bucket and one sale, shifting before sales "
        "creates phantom inventory next period. With one-period lead time, capacity on current orders constrains "
        "the wrong delivery period. With substitution, omitting inflow/outflow lets demand disappear."
    ),
)

SUBSTITUTION = SkillCard(
    skill_id="retail.substitution.v1",
    title="Substitution direction and inventory backing",
    questions=(
        Question("substitution_direction", "What does an edge (from,to) mean?", ("from_demand_is_fulfilled_by_to_inventory", "from_inventory_fulfills_to_demand"), "from_demand_is_fulfilled_by_to_inventory"),
        Question("substitution_demand_cap", "How is diverted demand bounded?", ("total_outbound_no_more_than_original_demand", "each_edge_no_more_than_total_inventory", "unbounded"), "total_outbound_no_more_than_original_demand"),
        Question("substitution_inventory_binding", "How is received substitute demand backed?", ("total_inbound_no_more_than_actual_sales_of_receiving_product", "no_inventory_binding", "inbound_no_more_than_lost_sales"), "total_inbound_no_more_than_actual_sales_of_receiving_product"),
    ),
    obligation=(
        "An edge from p to q diverts p-demand to inventory of q. Bound all outbound diversion from p by p's "
        "original demand, include inbound/outbound in demand conservation, and require inbound diverted demand "
        "to be backed by actual q sales."
    ),
    counterexample_witness=(
        "Witness: if q has no inventory but p has a high lost-sales penalty, an unbacked p-to-q flow can erase "
        "p demand at zero cost. The inbound-to-sales constraint rules out this fictitious improvement."
    ),
)

LEAD_TIME = SkillCard(
    skill_id="retail.lead_time.v1",
    title="Lead-time timing",
    questions=(
        Question("lead_time", "How does an order placed in period s arrive?", ("arrives_in_period_s_plus_lead_time", "arrives_same_period", "arrives_in_period_s_minus_lead_time"), "arrives_in_period_s_plus_lead_time"),
    ),
    obligation="Shift each order forward by its product-specific lead time; orders before the horizon are zero.",
    counterexample_witness="Witness: with lead time one and demand only in period one, a period-one order cannot serve period-one demand.",
)

MOQ_FIXED = SkillCard(
    skill_id="retail.moq_fixed.v1",
    title="MOQ and fixed-order activation",
    questions=(
        Question("order_activation", "How is a positive order linked to a binary activation?", ("lower_and_upper_link", "lower_link_only", "upper_link_only"), "lower_and_upper_link"),
        Question("fixed_order_cost", "How is a fixed order cost charged?", ("once_per_active_product_location_period", "per_ordered_unit", "once_per_product_over_horizon"), "once_per_active_product_location_period"),
    ),
    obligation="Use one binary per product-location-period, upper-link every positive order, lower-link MOQ when active, and charge a fixed cost once per active order.",
    counterexample_witness="Witness: a lower link without an upper link permits a positive order with an inactive binary and avoids the fixed cost.",
)

PACK_SIZE = SkillCard(
    skill_id="retail.pack_size.v1",
    title="Pack-size integrality",
    questions=(
        Question("pack_size", "How is an order restricted to full packs?", ("order_equals_pack_size_times_nonnegative_integer", "order_at_least_pack_size", "order_is_integer"), "order_equals_pack_size_times_nonnegative_integer"),
    ),
    obligation="Introduce a nonnegative integer pack count and set order quantity equal to pack size times that count.",
    counterexample_witness="Witness: an integer order of three units violates a four-unit pack even though it is integral and above no minimum.",
)

TRANSSHIPMENT = SkillCard(
    skill_id="retail.transshipment.v1",
    title="Network transshipment balance",
    questions=(
        Question("transshipment", "How does a location's transshipment affect fresh inflow?", ("incoming_minus_outgoing", "incoming_only", "outgoing_minus_incoming"), "incoming_minus_outgoing"),
    ),
    obligation="For every product, location and period, add incoming flows and subtract outgoing flows in the fresh-inflow balance.",
    counterexample_witness="Witness: counting incoming without outgoing duplicates every shipped unit across the network.",
)

RETURNS = SkillCard(
    skill_id="retail.returns.v1",
    title="Lagged reverse-logistics returns",
    questions=(
        Question("returns", "Which activity generates returns in period t?", ("previous_period_sales_times_return_rate", "same_period_sales_times_return_rate", "previous_period_orders_times_return_rate"), "previous_period_sales_times_return_rate"),
    ),
    obligation="Returns enter the freshest bucket one period after the sale that generated them; there are no returns in the first period.",
    counterexample_witness="Witness: same-period returns create a circular source of inventory that can support the sale that generated the return.",
)

LABOR = SkillCard(
    skill_id="retail.labor.v1",
    title="Labor capacity",
    questions=(
        Question("labor_capacity", "Which activity consumes retail labor capacity?", ("actual_sales", "orders_placed", "start_inventory"), "actual_sales"),
    ),
    obligation="Multiply product labor usage by actual sales and bound the location-period total by labor capacity.",
    counterexample_witness="Witness: capacity on orders does not constrain sales from existing inventory and therefore misses the operational bottleneck.",
)

BUDGET = SkillCard(
    skill_id="retail.budget.v1",
    title="Period purchasing budget",
    questions=(
        Question("budget", "Which cash flows consume a period budget?", ("purchase_cost_times_orders_plus_active_fixed_order_costs", "purchase_cost_times_arrivals", "sales_revenue"), "purchase_cost_times_orders_plus_active_fixed_order_costs"),
    ),
    obligation="Charge the period budget for orders placed in that period and include fixed activation costs when present.",
    counterexample_witness="Witness: with positive lead time, budgeting arrivals shifts cash expenditure to the wrong period.",
)

SUSTAINABILITY = SkillCard(
    skill_id="retail.sustainability.v1",
    title="Global waste limit",
    questions=(
        Question("waste_limit", "What is the denominator and scope of a waste percentage limit?", ("total_waste_over_horizon_le_fraction_of_total_demand", "each_period_waste_le_fraction_of_period_demand", "waste_cost_le_fraction_of_purchase_cost"), "total_waste_over_horizon_le_fraction_of_total_demand"),
    ),
    obligation="Apply one horizon-wide constraint: total physical waste cannot exceed the declared fraction of total physical demand.",
    counterexample_witness="Witness: per-period caps reject a plan that offsets a high-waste period with zero waste elsewhere even when the stated global fraction is satisfied.",
)


CARDS: tuple[SkillCard, ...] = (
    CORE,
    SUBSTITUTION,
    LEAD_TIME,
    MOQ_FIXED,
    PACK_SIZE,
    TRANSSHIPMENT,
    RETURNS,
    LABOR,
    BUDGET,
    SUSTAINABILITY,
)
CARD_BY_ID = {card.skill_id: card for card in CARDS}


def _any_positive(values: Mapping[str, Any]) -> bool:
    return any(isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 for value in values.values())


def route(data: Mapping[str, Any]) -> tuple[str, ...]:
    """Deterministically route public structured data to at most three cards."""

    required = {"constraints", "costs", "labor_usage", "lead_time", "network", "return_rate"}
    if not isinstance(data, Mapping) or not required.issubset(data):
        raise RetailKnowledgeError("data_schema")
    constraints = data["constraints"]
    costs = data["costs"]
    network = data["network"]
    if not all(isinstance(value, Mapping) for value in (constraints, costs, network)):
        raise RetailKnowledgeError("data_schema")
    selected = [CORE.skill_id]
    if network.get("sub_edges"):
        selected.append(SUBSTITUTION.skill_id)
    optional: list[str] = []
    if _any_positive(data["lead_time"]):
        optional.append(LEAD_TIME.skill_id)
    if (constraints.get("moq") or 0) > 0 or (costs.get("fixed_order") or 0) > 0:
        optional.append(MOQ_FIXED.skill_id)
    if (constraints.get("pack_size") or 1) > 1:
        optional.append(PACK_SIZE.skill_id)
    if network.get("trans_edges"):
        optional.append(TRANSSHIPMENT.skill_id)
    if _any_positive(data["return_rate"]):
        optional.append(RETURNS.skill_id)
    if _any_positive(data["labor_usage"]):
        optional.append(LABOR.skill_id)
    if constraints.get("budget_per_period") is not None:
        optional.append(BUDGET.skill_id)
    if constraints.get("waste_limit_pct") is not None:
        optional.append(SUSTAINABILITY.skill_id)
    if len(optional) > 1:
        raise RetailKnowledgeError("non_sparse_optional_route")
    selected.extend(optional)
    if len(selected) > 3:
        raise RetailKnowledgeError("route_card_budget")
    return tuple(selected)


def questions(selected_skill_ids: Iterable[str]) -> tuple[Question, ...]:
    result: list[Question] = []
    seen: set[str] = set()
    for skill_id in selected_skill_ids:
        card = CARD_BY_ID.get(skill_id)
        if card is None:
            raise RetailKnowledgeError("unknown_skill")
        for question in card.questions:
            if question.question_id in seen:
                raise RetailKnowledgeError("duplicate_question")
            seen.add(question.question_id)
            result.append(question)
    return tuple(result)


def gold_decision(selected_skill_ids: Iterable[str]) -> dict[str, str]:
    return {question.question_id: question.correct for question in questions(selected_skill_ids)}


def library_payload() -> dict[str, Any]:
    return {
        "schema": "llm4or-retailopt190-skill-library-v1",
        "cards": [
            {
                "skill_id": card.skill_id,
                "title": card.title,
                "obligation": card.obligation,
                "counterexample_witness": card.counterexample_witness,
                "questions": [
                    {
                        "question_id": question.question_id,
                        "prompt": question.prompt,
                        "choices": list(question.choices),
                        "correct": question.correct,
                    }
                    for question in card.questions
                ],
            }
            for card in CARDS
        ],
        "privacy": {
            "contains_benchmark_instances": False,
            "contains_reference_objectives": False,
            "contains_model_outputs": False,
            "contains_evaluator_code": False,
        },
    }


def library_sha256() -> str:
    raw = json.dumps(library_payload(), ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def render_request(
    *,
    opaque_archetype_id: str,
    public_prompt: str,
    selected_skill_ids: Iterable[str],
    arm: str,
) -> dict[str, Any]:
    selected = tuple(selected_skill_ids)
    qs = questions(selected)
    if arm not in {"base_short", "knowledge_short"}:
        raise RetailKnowledgeError("arm")
    evidence = []
    if arm == "knowledge_short":
        evidence = [
            {
                "skill_id": CARD_BY_ID[skill_id].skill_id,
                "title": CARD_BY_ID[skill_id].title,
                "obligation": CARD_BY_ID[skill_id].obligation,
                "counterexample_witness": CARD_BY_ID[skill_id].counterexample_witness,
            }
            for skill_id in selected
        ]
    return {
        "schema": "llm4or-retailopt190-short-decision-request-v1",
        "arm": arm,
        "opaque_archetype_id": opaque_archetype_id,
        "task": public_prompt,
        "questions": [
            {"question_id": q.question_id, "prompt": q.prompt, "choices": list(q.choices)} for q in qs
        ],
        "evidence": evidence,
        "instructions": (
            "Return exactly one JSON object with schema llm4or-retailopt190-short-decision-v1 and an answers object. "
            "The answers object must contain every listed question_id exactly once, with one listed choice string. "
            "Do not return code, formulas, explanations, markdown, or additional keys."
        ),
    }


def parse_decision(value: Any, selected_skill_ids: Iterable[str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"schema", "answers"}:
        raise RetailKnowledgeError("decision_schema")
    if value["schema"] != "llm4or-retailopt190-short-decision-v1" or not isinstance(value["answers"], Mapping):
        raise RetailKnowledgeError("decision_schema")
    qs = questions(selected_skill_ids)
    expected = {question.question_id: set(question.choices) for question in qs}
    if set(value["answers"]) != set(expected):
        raise RetailKnowledgeError("decision_membership")
    answers: dict[str, str] = {}
    for key, choice in value["answers"].items():
        if not isinstance(choice, str) or choice not in expected[key]:
            raise RetailKnowledgeError("decision_choice")
        answers[key] = choice
    return answers


__all__ = [
    "CARDS",
    "CARD_BY_ID",
    "RetailKnowledgeError",
    "SkillCard",
    "Question",
    "gold_decision",
    "library_payload",
    "library_sha256",
    "parse_decision",
    "questions",
    "render_request",
    "route",
]
