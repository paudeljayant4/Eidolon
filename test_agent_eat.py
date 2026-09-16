"""Regression tests for the eat mechanic and no-food critical hunger behavior."""
import pytest
from dataclasses import dataclass, field
from unittest.mock import MagicMock

from agents._agent import Agent, AgentType, Needs, Personality, Position, Skills, Inventory, Relationships, RuleBasedPlanner
from simulation._types import ResourceType, WorldConfig, Resource, Market
from simulation.core import SimulationCore


def make_agent(hunger: float = 1.0, food_in_inventory: int = 0) -> Agent:
    """Create a test agent with specified hunger and food inventory."""
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


def make_core(resources=None, markets=None, width=10, height=10) -> SimulationCore:
    """Create a simulation core with the given resources and markets."""
    config = WorldConfig(width=width, height=height, seed=42)
    core = SimulationCore(config=config, seed=42)
    core.initialize()

    # Override resources and markets if provided
    if resources is not None:
        core.world["resources"] = resources
    if markets is not None:
        core.world["markets"] = markets

    return core


def make_food_resource(amount: int = 50) -> Resource:
    """Create a food resource."""
    return Resource(
        id="food-res-1",
        type=ResourceType.FOOD,
        amount=amount,
        maxAmount=150,
        position=Position(5, 5),
        regionId="region-5-5",
        growth_timer=0,
    )


def make_market_with_food(amount: int = 5) -> Market:
    """Create a market with food supplies."""
    market = Market(id="market-1", regionId="region-0-0")
    market.supplies[ResourceType.FOOD] = amount
    return market


class TestEatWithFoodAvailable:
    """Regression test: agent with food + elevated hunger."""

    def test_agent_with_food_eats_and_restores_hunger(self):
        """Agent has food in inventory and elevated hunger. After eat action,
        hunger should decrease and food inventory should decrease."""
        agent = make_agent(hunger=0.6, food_in_inventory=5)
        core = make_core()

        # Set up a decision for eat
        decision = agent.decide(
            perception=type("Perception", (), {
                "visible_resources": {"food": 30},
                "market_prices": {},
                "nearby_agents": [],
                "needs_state": {"hunger": 0.6},
            })(),
            needs={"hunger": 0.6, "inventory_food": 5, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0},
        )

        assert decision.action == "eat", f"Expected 'eat', got '{decision.action}'"

        # Store initial state
        initial_hunger = agent.needs.hunger
        initial_food = agent.inventory.resources.get("food", 0)

        # Execute the eat action
        events = agent.act(decision, core)

        # Verify hunger decreased (restored)
        assert agent.needs.hunger > initial_hunger, \
            f"Hunger should increase after eating: {initial_hunger} -> {agent.needs.hunger}"
        assert agent.needs.hunger <= 1.0, f"Hunger should not exceed 1.0: {agent.needs.hunger}"

        # Verify food inventory decreased
        final_food = agent.inventory.resources.get("food", 0)
        assert final_food < initial_food, \
            f"Food inventory should decrease: {initial_food} -> {final_food}"
        assert final_food == initial_food - 1, \
            f"Should consume exactly 1 food: {initial_food} -> {final_food}"

        # Verify fed event was emitted
        fed_events = [e for e in events if e["type"] == "fed"]
        assert len(fed_events) == 1, f"Should emit 1 fed event, got {len(fed_events)}"

    def test_multiple_eats_over_ticks(self):
        """Run N ticks with an agent that has food and elevated hunger.
        Hunger should be restored after eating, food inventory should
        decrease correctly."""
        N = 10
        agent = make_agent(hunger=0.5, food_in_inventory=10)
        core = make_core()

        for tick in range(N):
            perception = type("Perception", (), {
                "visible_resources": {"food": 30},
                "market_prices": {},
                "nearby_agents": [],
                "needs_state": {"hunger": agent.needs.hunger},
            })()
            needs = {"hunger": agent.needs.hunger, "inventory_food": agent.inventory.resources.get("food", 0),
                     "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
            decision = agent.decide(perception, needs)
            events = agent.act(decision, core)

        # After eating once (hunger 0.5 + 0.2 = 0.7, still < 0.7 is false so only eat once)
        # But if initial hunger is lower, agent can eat multiple times
        assert agent.inventory.resources.get("food", 0) < 10, \
            f"Food inventory should have decreased: {agent.inventory.resources.get('food', 0)}"


class TestNoFoodCriticalHunger:
    """Regression test: agent with zero food + critical hunger."""

    def test_agent_no_food_critical_hunger_does_not_crash(self):
        """Agent has zero food and critical hunger (< 0.3). The agent
        should not crash and should attempt to acquire food."""
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        core = make_core(resources=[make_food_resource(amount=50)])

        # Planner should choose seek_food when hunger < 0.3
        perception = type("Perception", (), {
            "visible_resources": {"food": 50},
            "market_prices": {},
            "nearby_agents": [],
            "needs_state": {"hunger": 0.2},
        })()
        needs = {"hunger": 0.2, "inventory_food": 0, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)

        assert decision.action == "seek_food", f"Expected 'seek_food', got '{decision.action}'"

        # Execute should not crash
        events = agent.act(decision, core)

        # Agent should have acquired food
        assert agent.inventory.resources.get("food", 0) > 0, \
            f"Agent should have acquired food from visible resources: {agent.inventory.resources.get('food', 0)}"

        # Should have resource_gathered event
        gather_events = [e for e in events if e["type"] == "resource_gathered"]
        assert len(gather_events) > 0, "Should have resource_gathered events"
        assert any(e["data"]["resource"] == "food" for e in gather_events), \
            "Should have gathered food resource"

    def test_agent_no_food_no_visible_resources_acquires_from_market(self):
        """Agent has zero food, critical hunger, and no visible resources.
        Should attempt to buy from market."""
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        market = make_market_with_food(amount=5)
        core = make_core(resources=[], markets=[market])

        perception = type("Perception", (), {
            "visible_resources": {},
            "market_prices": {"food": 1.0},
            "nearby_agents": [],
            "needs_state": {"hunger": 0.2},
        })()
        needs = {"hunger": 0.2, "inventory_food": 0, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        assert decision.action == "seek_food"

        events = agent.act(decision, core)

        # Should have acquired food from market
        assert agent.inventory.resources.get("food", 0) > 0, \
            f"Agent should have acquired food from market: {agent.inventory.resources.get('food', 0)}"

        gather_events = [e for e in events if e["type"] == "resource_gathered"]
        assert any(e["data"].get("source") == "market" for e in gather_events), \
            "Should have acquired food from market"

    def test_agent_no_food_no_resources_no_market_emits_hunger_motivation(self):
        """Agent has zero food, critical hunger, no visible resources, no market.
        Should emit hunger_motivation without crashing."""
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        core = make_core(resources=[], markets=[])

        perception = type("Perception", (), {
            "visible_resources": {},
            "market_prices": {},
            "nearby_agents": [],
            "needs_state": {"hunger": 0.2},
        })()
        needs = {"hunger": 0.2, "inventory_food": 0, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        assert decision.action == "seek_food"

        events = agent.act(decision, core)

        # Should have hunger_motivation event (no food available anywhere)
        hunger_events = [e for e in events if e["type"] == "hunger_motivation"]
        assert len(hunger_events) > 0, "Should emit hunger_motivation when no food available"
        assert any("no food available" in e["data"].get("reason", "") for e in hunger_events), \
            "Reason should indicate no food available"

        # Agent should not crash - food inventory remains 0
        assert agent.inventory.resources.get("food", 0) == 0, "Food inventory should remain 0"

    def test_critical_hunger_no_food_after_N_ticks(self):
        """Agent with zero food and critical hunger run N ticks.
        Should not crash and should produce the decided behavior."""
        N = 10
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        core = make_core(resources=[make_food_resource(amount=100)])

        for tick in range(N):
            perception = type("Perception", (), {
                "visible_resources": {"food": 100},
                "market_prices": {},
                "nearby_agents": [],
                "needs_state": {"hunger": agent.needs.hunger},
            })()
            needs = {"hunger": agent.needs.hunger, "inventory_food": 0,
                     "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
            decision = agent.decide(perception, needs)
            events = agent.act(decision, core)

        # Agent should have acquired food over N ticks
        assert agent.inventory.resources.get("food", 0) >= 0, "Should not crash"
        # Agent should have some food after N ticks of seeking
        assert agent.inventory.resources.get("food", 0) > 0, \
            f"Agent should have acquired food after {N} ticks: {agent.inventory.resources.get('food', 0)}"

    def test_critical_hunger_seek_food_planning(self):
        """Agent with critical hunger (< 0.3) should plan seek_food."""
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        core = make_core(resources=[make_food_resource(amount=50)])

        perception = type("Perception", (), {
            "visible_resources": {"food": 50},
            "market_prices": {},
            "nearby_agents": [],
            "needs_state": {"hunger": 0.2},
        })()
        needs = {"hunger": 0.2, "inventory_food": 0, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        assert decision.action == "seek_food", f"Expected seek_food, got {decision.action}"

        # No crash when executing
        events = agent.act(decision, core)
        assert agent.inventory.resources.get("food", 0) > 0, "Should have acquired food from seek_food"

    def test_eat_action_no_food_redirects_to_acquisition(self):
        """When eat action is chosen but inventory has no food,
        the agent should redirect to food acquisition from visible resources."""
        agent = make_agent(hunger=0.2, food_in_inventory=0)
        core = make_core(resources=[make_food_resource(amount=50)])

        # Manually create an eat decision (simulating the planner choosing eat)
        decision = type("PlannerDecision", (), {"action": "eat", "target": None, "priority": 0.7, "confidence": 0.8})()

        events = agent.act(decision, core)

        # Agent should have acquired food from resources
        assert agent.inventory.resources.get("food", 0) > 0, \
            "Agent should acquire food when eat has no inventory food"

        # Should have resource_gathered events
        gather_events = [e for e in events if e["type"] == "resource_gathered"]
        assert len(gather_events) > 0, "Should have acquired food via eat_redirect"

        # If food was acquired, no hunger_motivation for eat should exist
        # If food was NOT acquired, hunger_motivation should exist
        if agent.inventory.resources.get("food", 0) > 0:
            hunger_events = [e for e in events if e["type"] == "hunger_motivation" and "eat" in e["data"].get("action", "")]
            assert len(hunger_events) == 0, "Should not have hunger_motivation when food was acquired"
        else:
            hunger_events = [e for e in events if e["type"] == "hunger_motivation" and "eat" in e["data"].get("action", "")]
            assert len(hunger_events) > 0, "Should have hunger_motivation for eat action when no food available"


class TestDeterminism:
    """Verify determinism: same seed produces same results."""

    def test_same_seed_same_results(self):
        """Two agents with the same seed should produce the same outcomes."""
        agent1 = make_agent(hunger=0.6, food_in_inventory=5)
        agent2 = make_agent(hunger=0.6, food_in_inventory=5)
        core1 = make_core()
        core2 = make_core()

        # Both agents eat
        decision1 = agent1.decide(
            type("Perception", (), {"visible_resources": {"food": 30}, "market_prices": {}, "nearby_agents": [], "needs_state": {"hunger": 0.6}})(),
            needs={"hunger": 0.6, "inventory_food": 5, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0},
        )
        decision2 = agent2.decide(
            type("Perception", (), {"visible_resources": {"food": 30}, "market_prices": {}, "nearby_agents": [], "needs_state": {"hunger": 0.6}})(),
            needs={"hunger": 0.6, "inventory_food": 5, "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0},
        )

        events1 = agent1.act(decision1, core1)
        events2 = agent2.act(decision2, core2)

        # Same hunger restoration
        assert agent1.needs.hunger == agent2.needs.hunger, \
            f"Same seed should produce same hunger: {agent1.needs.hunger} vs {agent2.needs.hunger}"
        assert agent1.inventory.resources.get("food", 0) == agent2.inventory.resources.get("food", 0), \
            "Same seed should produce same food inventory"
        # Same event types
        assert [e["type"] for e in events1] == [e["type"] for e in events2], \
            "Same seed should produce same event types"

    def test_determinism_after_multiple_ticks(self):
        """Same seed + same inputs should produce same results after N ticks."""
        N = 5
        results_run1 = []
        results_run2 = []

        for _ in range(2):
            agent = make_agent(hunger=0.8, food_in_inventory=3)
            core = make_core()
            hunger_vals = []
            food_vals = []
            for tick in range(N):
                perception = type("Perception", (), {
                    "visible_resources": {"food": 30},
                    "market_prices": {},
                    "nearby_agents": [],
                    "needs_state": {"hunger": agent.needs.hunger},
                })()
                needs = {"hunger": agent.needs.hunger, "inventory_food": agent.inventory.resources.get("food", 0),
                         "thirst": 1.0, "rest": 1.0, "social": 1.0, "safety": 1.0}
                decision = agent.decide(perception, needs)
                agent.act(decision, core)
                hunger_vals.append(round(agent.needs.hunger, 4))
                food_vals.append(agent.inventory.resources.get("food", 0))
            results_run1.append((hunger_vals, food_vals))

        assert results_run1[0] == results_run1[1], \
            "Determinism check failed: same seed should produce same results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
