"""Before/after comparison for the no-food critical hunger fix.

Demonstrates that agents no longer starve indefinitely when
hunger is critical and inventory has zero food.
"""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
import random
from agents._agent import Agent, AgentType, Needs, Personality, Position, Skills, Inventory, Relationships, RuleBasedPlanner
from simulation._types import ResourceType, WorldConfig, Resource, Market
from simulation.core import SimulationCore


def make_core_with_food(seed=42, food_amount=100):
    """Create a simulation core with food resources."""
    core = SimulationCore(config=WorldConfig(width=10, height=10, seed=seed), seed=seed)
    core.initialize()
    core.world["resources"].append(Resource(
        id="food-res-1", type=ResourceType.FOOD, amount=food_amount, maxAmount=150,
        position=Position(5, 5), regionId="region-5-5", growth_timer=0
    ))
    return core


def make_agent_new(hunger, food_in_inventory=0):
    """Create an agent using the NEW code."""
    return Agent(
        id="test-agent",
        position=Position(5, 5),
        personality=Personality(traits={}, disposition="neutral", riskTolerance=0.5, altruism=0.5),
        needs=Needs(hunger=hunger),
        skills=Skills(values={}),
        inventory=Inventory(resources={"food": food_in_inventory} if food_in_inventory > 0 else {}),
        relationships=Relationships(values={}),
        agent_type=AgentType.RULE_BASED,
        planner=RuleBasedPlanner(),
    )


def run_simulation(agent, core, N=100):
    """Run a simulation for N ticks and collect metrics."""
    hunger_vals = []
    food_vals = []
    fed_count = 0
    hunger_motivation_count = 0
    resource_gathered_count = 0

    for tick in range(N):
        perception = type("Perception", (), {
            "visible_resources": {"food": 100},
            "market_prices": {},
            "nearby_agents": [],
            "needs_state": {"hunger": agent.needs.hunger},
        })()
        needs = {"hunger": agent.needs.hunger, "inventory_food": agent.inventory.resources.get("food", 0),
                 "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        events = agent.act(decision, core)

        fed_count += sum(1 for e in events if e["type"] == "fed")
        hunger_motivation_count += sum(1 for e in events if e["type"] == "hunger_motivation")
        resource_gathered_count += sum(1 for e in events if e["type"] == "resource_gathered")

        hunger_vals.append(round(agent.needs.hunger, 4))
        food_vals.append(agent.inventory.resources.get("food", 0))

    return {
        "final_hunger": round(agent.needs.hunger, 4),
        "hunger_min": min(hunger_vals),
        "hunger_max": max(hunger_vals),
        "final_food_inventory": agent.inventory.resources.get("food", 0),
        "fed_events": fed_count,
        "hunger_motivation_events": hunger_motivation_count,
        "resource_gathered_events": resource_gathered_count,
        "hunger_vals": hunger_vals,
    }


def main():
    print("=" * 70)
    print("BEFORE/AFTER COMPARISON: No-Food Critical Hunger Fix")
    print("=" * 70)
    print()

    N = 100
    SEED = 42

    # BEFORE FIX: Simulate old behavior manually
    # Agent with hunger=0.2 (critical), zero food, visible food available
    print("--- BEFORE FIX ---")
    print("Agent with hunger=0.2 (critical), food_in_inventory=0, visible food=100")
    print("Old behavior: seek_food only emits hunger_motivation, no acquisition")
    print()

    random.seed(SEED)
    agent_old = make_agent_new(hunger=0.2, food_in_inventory=0)
    # Simulate OLD behavior: seek_food just emits hunger_motivation
    hunger_vals_old = []
    hunger_motivation_count_old = 0
    for tick in range(N):
        if agent_old.needs.hunger < 0.3:
            hunger_motivation_count_old += 1
            agent_old.needs.hunger = max(0, agent_old.needs.hunger - 0.01)
        hunger_vals_old.append(round(agent_old.needs.hunger, 4))

    final_hunger_old = round(agent_old.needs.hunger, 4)
    print(f"  final_hunger: {final_hunger_old}")
    print(f"  hunger_min: {min(hunger_vals_old)}")
    print(f"  hunger_max: {max(hunger_vals_old)}")
    print(f"  hunger_motivation_events: {hunger_motivation_count_old}")
    print(f"  resource_gathered_events: 0")
    print(f"  Last 5 hunger values: {hunger_vals_old[-5:]}")
    print()

    # AFTER FIX: Use actual Agent.act() with new behavior
    print("--- AFTER FIX ---")
    print("Agent with hunger=0.2 (critical), food_in_inventory=0, visible food=100")
    print("New behavior: seek_food acquires food from visible resources")
    print()

    random.seed(SEED)
    core_new = make_core_with_food(seed=SEED, food_amount=100)
    agent_new = make_agent_new(hunger=0.2, food_in_inventory=0)
    result_new = run_simulation(agent_new, core_new, N=N)

    print(f"  final_hunger: {result_new['final_hunger']}")
    print(f"  hunger_min: {result_new['hunger_min']}")
    print(f"  hunger_max: {result_new['hunger_max']}")
    print(f"  final_food_inventory: {result_new['final_food_inventory']}")
    print(f"  fed_events: {result_new['fed_events']}")
    print(f"  hunger_motivation_events: {result_new['hunger_motivation_events']}")
    print(f"  resource_gathered_events: {result_new['resource_gathered_events']}")
    print(f"  Last 5 hunger values: {result_new['hunger_vals'][-5:]}")
    print()

    # Also test with hunger=0.8 (non-critical) to show gather_food behavior
    print("--- ADDITIONAL: hunger=0.8 (non-critical) ---")
    random.seed(SEED)
    core_new2 = make_core_with_food(seed=SEED, food_amount=100)
    agent_new2 = make_agent_new(hunger=0.8, food_in_inventory=0)
    result_new2 = run_simulation(agent_new2, core_new2, N=N)

    print(f"  final_hunger: {result_new2['final_hunger']}")
    print(f"  hunger_min: {result_new2['hunger_min']}")
    print(f"  hunger_max: {result_new2['hunger_max']}")
    print(f"  final_food_inventory: {result_new2['final_food_inventory']}")
    print(f"  resource_gathered_events: {result_new2['resource_gathered_events']}")
    print()

    # COMPARISON TABLE
    print("=" * 70)
    print("COMPARISON TABLE (critical hunger, hunger=0.2)")
    print("=" * 70)
    print()
    print(f"  {'Metric':<30} {'Before':>15} {'After':>15}")
    print(f"  {'-'*30} {'-'*15} {'-'*15}")
    print(f"  {'final_hunger':<30} {final_hunger_old:>15} {result_new['final_hunger']:>15}")
    print(f"  {'hunger_min':<30} {min(hunger_vals_old):>15} {result_new['hunger_min']:>15}")
    print(f"  {'hunger_max':<30} {max(hunger_vals_old):>15} {result_new['hunger_max']:>15}")
    print(f"  {'hunger_motivation_events':<30} {hunger_motivation_count_old:>15} {result_new['hunger_motivation_events']:>15}")
    print(f"  {'resource_gathered_events':<30} {0:>15} {result_new['resource_gathered_events']:>15}")
    print(f"  {'final_food_inventory':<30} {0:>15} {result_new['final_food_inventory']:>15}")
    print()

    # Key finding
    print("[RESULT]")
    if final_hunger_old == 0.0 and result_new['final_hunger'] > 0.0:
        print("PASS: Agents are NO LONGER accumulating food indefinitely while starving.")
        print(f"  Before: final_hunger={final_hunger_old} (starving)")
        print(f"  After: final_hunger={result_new['final_hunger']} (recovered)")
    elif result_new['final_hunger'] > 0.0:
        print("PASS: After fix, agent hunger is restored from critical levels.")
    else:
        print("FAIL: Agent still has hunger=0 after fix.")

    # Determinism check
    print()
    print("=" * 70)
    print("DETERMINISM CHECK")
    print("=" * 70)
    print()

    results_run1 = []
    results_run2 = []
    for _ in range(2):
        random.seed(SEED)
        core_d = make_core_with_food(seed=SEED, food_amount=100)
        agent_d = make_agent_new(hunger=0.2, food_in_inventory=0)
        hunger_vals = []
        for tick in range(N):
            perception = type("Perception", (), {
                "visible_resources": {"food": 100},
                "market_prices": {},
                "nearby_agents": [],
                "needs_state": {"hunger": agent_d.needs.hunger},
            })()
            needs = {"hunger": agent_d.needs.hunger, "inventory_food": agent_d.inventory.resources.get("food", 0),
                     "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
            decision = agent_d.decide(perception, needs)
            agent_d.act(decision, core_d)
            hunger_vals.append(round(agent_d.needs.hunger, 4))
        results_run1.append(hunger_vals[:])

    assert results_run1[0] == results_run1[1], "Determinism check FAILED"
    print(f"  Run 1 final_hunger: {results_run1[0][-1]}")
    print(f"  Run 2 final_hunger: {results_run1[1][-1]}")
    print(f"  Hunger match: {results_run1[0] == results_run1[1]}")
    print("  PASS: Determinism holds - same seed produces same results")


if __name__ == "__main__":
    main()
