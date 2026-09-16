"""Regression tests for emergent depth — social system, multi-agent world."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
import pytest
from agents._agent import Agent, AgentType, Needs, Personality, Position, Skills, Inventory, Relationships
from simulation._types import WorldConfig, ResourceType, Organization
from simulation.core import SimulationCore


def make_core(seed=42):
    """Create a simulation core with multi-agent world."""
    core = SimulationCore(config=WorldConfig(width=10, height=10, seed=seed), seed=seed)
    core.initialize()
    return core


def make_agent(hunger=0.5, social=0.5):
    """Create a test agent."""
    return Agent(
        id="test-agent",
        position=Position(5, 5),
        personality=Personality(traits={}, disposition="neutral", riskTolerance=0.5, altruism=0.5),
        needs=Needs(hunger=hunger, social=social),
        skills=Skills(values={}),
        inventory=Inventory(),
        relationships=Relationships(values={}),
        agent_type=AgentType.RULE_BASED,
    )


class TestMultiAgentWorld:
    """Multi-agent world generation."""

    def test_multiple_agents_generated(self):
        """World should contain multiple agents."""
        core = make_core(seed=42)
        agents = core.world.get("agents", [])
        assert len(agents) >= 5, f"Expected at least 5 agents, got {len(agents)}"

    def test_organization_generated(self):
        """World should contain an organization."""
        core = make_core(seed=42)
        orgs = core.world.get("organizations", [])
        assert len(orgs) >= 1, "Expected at least 1 organization"
        assert orgs[0].name == "Main Guild"

    def test_agent_organization_assignment(self):
        """Agent 0 should be assigned to the main organization."""
        core = make_core(seed=42)
        agent_0 = core.world["agent"]
        assert agent_0.organization is not None, "Agent 0 should have an organization"
        assert agent_0.organization == "org-main-42"


class TestSocializeMechanics:
    """Socialize action mechanics."""

    def test_socialize_modifies_relationship(self):
        """Socializing with a target should modify relationship values."""
        core = make_core(seed=42)
        agent = make_agent(social=0.1)
        target = "agent-1"

        decision = type("PlannerDecision", (), {"action": "socialize", "target": target, "priority": 0.5, "confidence": 0.6})()
        events = agent.act(decision, core)

        # Relationship should be modified
        rel_val = agent.relationships.values.get(target, 0.0)
        assert rel_val > 0, f"Relationship should be positive after socializing: {rel_val}"

        # Social need should be partially satisfied
        assert agent.needs.social > 0.1, f"Social need should increase: {agent.needs.social}"

        # Social memory should be created
        social_memories = [m for m in agent.memory.social if m.related_agent_id == target]
        assert len(social_memories) > 0, "Should have created social memory"

    def test_socialize_creates_social_memory(self):
        """Socializing should add entries to social memory."""
        core = make_core(seed=42)
        agent = make_agent(social=0.1)
        target = "agent-2"

        decision = type("PlannerDecision", (), {"action": "socialize", "target": target, "priority": 0.5, "confidence": 0.6})()
        events = agent.act(decision, core)

        social_memories = agent.memory.social
        assert len(social_memories) > 0, "Should have social memories"
        assert any(m.related_agent_id == target for m in social_memories), \
            "Should have social memory for target"

    def test_socialize_no_target_emits_reason(self):
        """Socializing without a target should emit a reason."""
        core = make_core(seed=42)
        agent = make_agent()

        decision = type("PlannerDecision", (), {"action": "socialize", "target": None, "priority": 0.5, "confidence": 0.6})()
        events = agent.act(decision, core)

        no_target_events = [e for e in events if "no nearby agents" in e["data"].get("reason", "")]
        assert len(no_target_events) > 0, "Should emit reason for no target"

    def test_socialize_no_agents_world_does_not_crash(self):
        """Social interaction handler should not raise when world has no agents."""
        core = make_core(seed=42)
        core.world["agents"] = []
        event = type("Event", (), {"type": "social_interaction", "source": "agent-0", "data": {"target": "agent-1", "relationship_value": 0.3}})()
        core._handle_social_interaction(core.world, event, {"target": "agent-1", "relationship_value": 0.3})

    def test_socialize_missing_agents_key_does_not_crash(self):
        """Social interaction handler should not raise when world lacks agents key."""
        core = make_core(seed=42)
        del core.world["agents"]
        event = type("Event", (), {"type": "social_interaction", "source": "agent-0", "data": {"target": "agent-1", "relationship_value": 0.3}})()
        core._handle_social_interaction(core.world, event, {"target": "agent-1", "relationship_value": 0.3})


class TestSocialNeedInPlanner:
    """Social need should influence planning."""

    def test_low_social_triggers_socialize(self):
        """Agent with low social need and nearby agents should plan socialize."""
        core = make_core(seed=42)
        agent = make_agent(hunger=0.5, social=0.1)
        perception = type("Perception", (), {
            "visible_resources": {},
            "market_prices": {},
            "nearby_agents": ["agent-1"],
            "needs_state": {"hunger": 0.5, "social": 0.1},
        })()
        needs = {"hunger": 0.5, "social": 0.1, "inventory_food": 0,
                 "thirst": 1.0, "rest": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        assert decision.action == "socialize", f"Expected socialize, got {decision.action}"

    def test_normal_social_no_socialize(self):
        """Agent with normal social need should not plan socialize."""
        core = make_core(seed=42)
        agent = make_agent(hunger=0.5, social=0.8)
        perception = type("Perception", (), {
            "visible_resources": {},
            "market_prices": {},
            "nearby_agents": ["agent-1"],
            "needs_state": {"hunger": 0.5, "social": 0.8},
        })()
        needs = {"hunger": 0.5, "social": 0.8, "inventory_food": 0,
                 "thirst": 1.0, "rest": 1.0, "safety": 1.0}
        decision = agent.decide(perception, needs)
        assert decision.action != "socialize", f"Should not socialize when social need is normal: {decision.action}"


class TestOrganizationMechanics:
    """Organization formation and joining."""

    def test_form_organization_creates_org(self):
        """Forming an organization should set agent's organization field."""
        agent = make_agent()
        core = make_core(seed=42)

        decision = type("PlannerDecision", (), {"action": "form_organization", "target": None, "priority": 0.5, "confidence": 0.6})()
        events = agent.act(decision, core)

        assert agent.organization is not None, "Agent should have an organization"
        org_events = [e for e in events if e["type"] == "organization_formed"]
        assert len(org_events) > 0, "Should emit organization_formed event"

    def test_join_organization_sets_field(self):
        """Joining an organization should set agent's organization field."""
        agent = make_agent()
        core = make_core(seed=42)
        target_org = "org-main-42"

        decision = type("PlannerDecision", (), {"action": "join_organization", "target": target_org, "priority": 0.5, "confidence": 0.6})()
        events = agent.act(decision, core)

        assert agent.organization == target_org, f"Agent should be in {target_org}"
        join_events = [e for e in events if e["type"] == "joined_organization"]
        assert len(join_events) > 0, "Should emit joined_organization event"


class TestDeterminismEmergentDepth:
    """Verify determinism for emergent depth features."""

    def test_multi_agent_world_determinism(self):
        """Same seed should produce same agent configurations."""
        core1 = make_core(seed=42)
        core2 = make_core(seed=42)

        agents1 = core1.world.get("agents", [])
        agents2 = core2.world.get("agents", [])

        assert len(agents1) == len(agents2), "Same number of agents"
        for a1, a2 in zip(agents1, agents2):
            assert a1.personality.disposition == a2.personality.disposition, \
                f"Same disposition for {a1.id} and {a2.id}"

    def test_socialize_determinism(self):
        """Same seed should produce same social interactions."""
        agent1 = make_agent(social=0.1)
        agent2 = make_agent(social=0.1)
        core1 = make_core(seed=42)
        core2 = make_core(seed=42)

        target = "agent-1"
        decision1 = type("PlannerDecision", (), {"action": "socialize", "target": target, "priority": 0.5, "confidence": 0.6})()
        decision2 = type("PlannerDecision", (), {"action": "socialize", "target": target, "priority": 0.5, "confidence": 0.6})()

        events1 = agent1.act(decision1, core1)
        events2 = agent2.act(decision2, core2)

        assert agent1.relationships.values.get(target, 0.0) == agent2.relationships.values.get(target, 0.0), \
            "Same seed should produce same relationship values"
        assert [e["type"] for e in events1] == [e["type"] for e in events2], \
            "Same seed should produce same event types"

    def test_organization_determinism(self):
        """Same seed should produce same organizations."""
        core1 = make_core(seed=42)
        core2 = make_core(seed=42)

        orgs1 = core1.world.get("organizations", [])
        orgs2 = core2.world.get("organizations", [])

        assert len(orgs1) == len(orgs2), "Same number of organizations"
        assert orgs1[0].id == orgs2[0].id, "Same organization ID"
        assert orgs1[0].name == orgs2[0].name, "Same organization name"

    def test_market_update_throttled(self):
        """Market prices should only update every MARKET_UPDATE_INTERVAL ticks."""
        core = make_core(seed=42)
        core.MARKET_UPDATE_INTERVAL = 5
        # Set up market supplies/demands so price events are emitted
        for market in core.world.get("markets", []):
            market.demands[ResourceType.FOOD] = 10
            market.supplies[ResourceType.FOOD] = 5
        
        # Tick 0: markets should update
        events_tick0 = core.tick_step()
        market_events_tick0 = [e for e in events_tick0 if e.type == "price_changed"]
        
        # Tick 1: markets should NOT update
        events_tick1 = core.tick_step()
        market_events_tick1 = [e for e in events_tick1 if e.type == "price_changed"]
        
        # Tick 2, 3, 4: markets should NOT update
        for _ in range(3):
            core.tick_step()
        
        # Tick 5: markets should update again
        events_tick5 = core.tick_step()
        market_events_tick5 = [e for e in events_tick5 if e.type == "price_changed"]
        
        assert len(market_events_tick0) > 0, "Markets should update on tick 0"
        assert len(market_events_tick1) == 0, "Markets should NOT update on tick 1"
        assert len(market_events_tick5) > 0, "Markets should update on tick 5"
        
    def test_market_events_batched(self):
        """Market price changes should be batched into single events per market."""
        core = make_core(seed=42)
        core.MARKET_UPDATE_INTERVAL = 1
        for market in core.world.get("markets", []):
            market.demands[ResourceType.FOOD] = 10
            market.supplies[ResourceType.FOOD] = 5
        
        events = core.tick_step()
        market_events = [e for e in events if e.type == "price_changed"]
        
        for e in market_events:
            assert "price_changes" in e.data, "Event should have batched price_changes"
            assert isinstance(e.data["price_changes"], dict), "price_changes should be a dict"

    def test_building_production_emits_events(self):
        """Buildings should produce resources and emit events."""
        core = make_core(seed=42)
        # Run a few ticks to trigger building production
        events = core.tick_step()
        production_events = [e for e in events if e.type == "building_production"]
        # Should have production events for farms, lumber camps, etc.
        assert len(production_events) > 0, "Should have building_production events"
        
    def test_buildings_have_production_consumption(self):
        """Buildings from world generation should have resourcesProduced and resourcesConsumed."""
        core = make_core(seed=42)
        buildings = core.world.get("buildings", [])
        assert len(buildings) > 0, "Should have buildings"
        for b in buildings:
            assert hasattr(b, "resourcesProduced"), "Building should have resourcesProduced"
            assert hasattr(b, "resourcesConsumed"), "Building should have resourcesConsumed"
            # At least some buildings should produce something
            if b.type.value in ["farm", "lumber_camp", "mine", "workshop", "quarry"]:
                assert len(b.resourcesProduced) > 0, f"{b.type} should produce resources"
        
    def test_building_production_replay(self):
        """Building production should be replayable."""
        core = make_core(seed=42)
        core.tick_step()
        events = core.event_log.events
        prod_events = [e for e in events if e.type == "building_production"]
        
        # Replay
        replayed = core.replay_tick(core.tick)
        replayed_buildings = replayed["world"].get("buildings", [])
        original_buildings = core.world.get("buildings", [])
        assert len(replayed_buildings) == len(original_buildings), "Buildings should replay"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
