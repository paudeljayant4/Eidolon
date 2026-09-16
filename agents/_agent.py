from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import random
import json
import time
from simulation._types import Needs, Personality, Position, Skills, Inventory, Relationships, ResourceType, Organization


class AgentType(Enum):
    RULE_BASED = "rule_based"
    LLM_BACKED = "llm_backed"


class MemoryTier(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    SOCIAL = "social"


@dataclass
class MemoryItem:
    """Base memory item."""
    id: str
    tier: MemoryTier
    content: dict
    timestamp: float
    salience: float = 1.0
    access_count: int = 0
    emotional_weight: float = 1.0


@dataclass
class EpisodicMemory(MemoryItem):
    """Specific events: 'visited the market yesterday'."""
    source_event_id: str = ""


@dataclass
class SemanticMemory(MemoryItem):
    """Generalized facts: 'iron is expensive up north'."""
    generalized_from: list[str] = field(default_factory=list)


@dataclass
class SocialMemory(MemoryItem):
    """Relationship-relevant: 'Arin helped me during the shortage'."""
    related_agent_id: str = ""


@dataclass
class AgentMemory:
    """Three-tier memory system with emotional salience weighting."""
    episodic: list[EpisodicMemory] = field(default_factory=list)
    semantic: list[SemanticMemory] = field(default_factory=list)
    social: list[SocialMemory] = field(default_factory=list)

    def add_episodic(self, content: dict, source_event_id: str = "") -> EpisodicMemory:
        item = EpisodicMemory(
            id=f"episodic-{int(time.time()*1000)}-{len(self.episodic)}",
            tier=MemoryTier.EPISODIC,
            content=content,
            timestamp=time.time(),
            source_event_id=source_event_id
        )
        self.episodic.append(item)
        if len(self.episodic) > 100:
            self.episodic = self.episodic[-100:]
        return item

    def add_semantic(self, content: dict, generalized_from: list[str] | None = None) -> SemanticMemory:
        item = SemanticMemory(
            id=f"semantic-{int(time.time()*1000)}-{len(self.semantic)}",
            tier=MemoryTier.SEMANTIC,
            content=content,
            timestamp=time.time()
        )
        if generalized_from:
            item.generalized_from = generalized_from
        self.semantic.append(item)
        if len(self.semantic) > 50:
            self.semantic = self.semantic[-50:]
        return item

    def add_social(self, related_agent_id: str, content: dict, emotional_weight: float = 1.0) -> SocialMemory:
        item = SocialMemory(
            id=f"social-{int(time.time()*1000)}-{len(self.social)}",
            tier=MemoryTier.SOCIAL,
            content=content,
            timestamp=time.time(),
            related_agent_id=related_agent_id,
            emotional_weight=emotional_weight
        )
        self.social.append(item)
        if len(self.social) > 50:
            self.social = self.social[-50:]
        return item

    def recall_episodic(self, limit: int = 10, min_salience: float = 0.0) -> list[EpisodicMemory]:
        filtered = [m for m in self.episodic if m.salience >= min_salience]
        filtered.sort(key=lambda m: m.salience * m.timestamp, reverse=True)
        return filtered[:limit]

    def recall_semantic(self, limit: int = 10) -> list[SemanticMemory]:
        return sorted(
            self.semantic,
            key=lambda m: m.access_count * m.salience,
            reverse=True
        )[:limit]

    def recall_social(self, agent_id: str, limit: int = 10) -> list[SocialMemory]:
        filtered = [m for m in self.social if m.related_agent_id == agent_id]
        return sorted(
            filtered,
            key=lambda m: m.emotional_weight,
            reverse=True
        )[:limit]

    def consolidate(self):
        """Promote important episodic memories to semantic."""
        important = [m for m in self.episodic if m.salience >= 0.7]
        for mem in important:
            self.add_semantic(content=mem.content, generalized_from=[mem.id])
            self.episodic.remove(mem)


@dataclass
class Perception:
    """What the agent perceives from the world state."""
    visible_resources: dict[str, int] = field(default_factory=dict)
    nearby_agents: list[str] = field(default_factory=list)
    nearby_buildings: list[str] = field(default_factory=list)
    market_prices: dict[str, float] = field(default_factory=dict)
    needs_state: dict[str, float] = field(default_factory=dict)


@dataclass
class PlannerDecision:
    """Result from the planner module."""
    action: str
    target: str | None = None
    priority: float = 0.5
    confidence: float = 0.5


class BasePlanner(ABC):
    """Abstract base class for agent planners."""

    @abstractmethod
    def plan(self, perception: Perception, memory: AgentMemory, needs: dict) -> PlannerDecision:
        pass


class RuleBasedPlanner(BasePlanner):
    """Rule-based planner for affordable large-population runs."""

    def plan(self, perception: Perception, memory: AgentMemory, needs: dict) -> PlannerDecision:
        action = "move"
        target = None
        priority = 0.5
        confidence = 0.7

        # Priority 1: Eat if we have food and are hungry (takes precedence)
        if needs.get("inventory_food", 0) > 0 and needs.get("hunger", 1.0) < 0.7:
            action = "eat"
            priority = 0.8
            confidence = 0.8

        # Priority 2: Satisfy urgent needs (only if we have no food to eat)
        elif needs.get("hunger", 1.0) < 0.3:
            action = "seek_food"
            confidence = 0.9
            priority = 1.0
        elif needs.get("thirst", 1.0) < 0.3:
            action = "seek_water"
            confidence = 0.9
            priority = 1.0
        elif needs.get("rest", 1.0) < 0.3:
            action = "rest"
            confidence = 0.8
            priority = 0.8

        # Priority 3: Social need — socialize if social is low and nearby agents exist
        elif needs.get("social", 1.0) < 0.3 and perception.nearby_agents:
            action = "socialize"
            target = perception.nearby_agents[0]
            priority = 0.5
            confidence = 0.6

        # Priority 4: Economic actions
        elif perception.visible_resources.get("wood", 0) > 50:
            action = "gather_wood"
            priority = 0.6
            confidence = 0.7
        elif perception.visible_resources.get("iron", 0) > 20:
            action = "gather_iron"
            priority = 0.6
            confidence = 0.7
        elif perception.visible_resources.get("food", 0) > 30:
            action = "gather_food"
            priority = 0.5
            confidence = 0.6

        # Priority 5: Social actions (general, not urgent)
        elif perception.nearby_agents and needs.get("social", 1.0) < 0.6:
            action = "socialize"
            target = perception.nearby_agents[0]
            priority = 0.4
            confidence = 0.5

        # Priority 6: Explore
        else:
            action = "explore"
            priority = 0.3
            confidence = 0.4

        return PlannerDecision(
            action=action,
            target=target,
            priority=priority,
            confidence=confidence
        )


class LLMBasedPlanner(BasePlanner):
    """LLM-backed planner via tool-calling."""

    def __init__(self, tool_caller=None, embeddings_client=None, vector_db=None):
        self.tool_caller = tool_caller
        self.embeddings_client = embeddings_client
        self.vector_db = vector_db

    def plan(self, perception: Perception, memory: AgentMemory, needs: dict) -> PlannerDecision:
        memory_context = self._build_memory_context(memory)
        world_state = self._query_world_state(perception)
        prompt = self._build_prompt(needs, memory_context, world_state)

        try:
            response = self.tool_caller.call_tools(prompt) if self.tool_caller else ""
            decision = self._parse_llm_response(response)
        except Exception:
            decision = RuleBasedPlanner().plan(perception, memory, needs)

        return decision

    def _build_memory_context(self, memory: AgentMemory) -> str:
        parts = []
        recent_episodic = memory.recall_episodic(limit=5, min_salience=0.5)
        for mem in recent_episodic:
            parts.append(f"Episodic: {mem.content}")
        semantic = memory.recall_semantic(limit=3)
        for mem in semantic:
            parts.append(f"Semantic: {mem.content}")
        parts.append("Social: (agent-specific relationships)")
        return " | ".join(parts) if parts else "No prior memories"

    def _query_world_state(self, perception: Perception) -> dict:
        return {
            "visible_resources": perception.visible_resources,
            "market_prices": perception.market_prices,
            "nearby_agents": perception.nearby_agents
        }

    def _build_prompt(self, needs: dict, memory_context: str, world_state: dict) -> str:
        needs_str = ", ".join(f"{k}: {v:.2f}" for k, v in needs.items())
        return f"""You are an autonomous agent in a simulation. 
Current needs: {needs_str}
Memory: {memory_context}
World state: {json.dumps(world_state, indent=2)}

Choose an action: move, seek_food, seek_water, rest, gather_wood, gather_iron,
gather_food, socialize, explore, trade, form_organization,
join_organization, build. Respond with just the action name."""

    def _parse_llm_response(self, response: str) -> PlannerDecision:
        action = response.strip().lower()
        valid_actions = [
            "move", "seek_food", "seek_water", "rest",
            "gather_wood", "gather_iron", "gather_food",
            "eat", "socialize", "explore", "trade",
            "form_organization", "join_organization", "build"
        ]
        if action not in valid_actions:
            action = "move"
        return PlannerDecision(action=action, priority=0.5, confidence=0.7)


@dataclass
class Agent:
    """Agent with cognitive architecture and ECS-style components."""
    id: str
    position: Position
    personality: Personality
    needs: Needs
    skills: Skills
    inventory: Inventory
    relationships: Relationships
    agent_type: AgentType = AgentType.RULE_BASED
    memory: AgentMemory = field(default_factory=AgentMemory)
    organization: Optional[str] = None
    health: float = 1.0
    energy: float = 1.0
    planner: BasePlanner | None = None

    def perceive(self, world_state: dict) -> Perception:
        perception = Perception()
        if "resources" in world_state:
            for res in world_state["resources"]:
                rtype = res.type
                if rtype not in perception.visible_resources:
                    perception.visible_resources[rtype] = 0
                perception.visible_resources[rtype] += res.amount
        if "markets" in world_state:
            for market in world_state["markets"]:
                for rtype, price in market.prices.items():
                    perception.market_prices[rtype] = price
        if "needs" in world_state:
            perception.needs_state = world_state["needs"]
        return perception

    def decide(self, perception: Perception, needs: dict) -> PlannerDecision:
        if self.planner is not None:
            return self.planner.plan(perception, self.memory, needs)
        else:
            return RuleBasedPlanner().plan(perception, self.memory, needs)

    def act(self, decision: PlannerDecision, core) -> list:
        events = []
        action = decision.action
        target = decision.target

        if action == "move":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(core.config.width - 1, self.position.x + dx))
            new_y = max(0, min(core.config.height - 1, self.position.y + dy))
            self.position.x = new_x
            self.position.y = new_y
            events.append({
                "type": "moved",
                "data": {"x": self.position.x, "y": self.position.y, "dx": dx, "dy": dy}
            })

        elif action == "seek_food":
            food_acquired = False
            for res in core.world.get("resources", []):
                if res.type == ResourceType.FOOD and res.amount > 0:
                    self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 15
                    res.amount -= 1
                    events.append({
                        "type": "resource_gathered",
                        "data": {"resource": "food", "amount": 15}
                    })
                    food_acquired = True
                    break
            if not food_acquired:
                for market in core.world.get("markets", []):
                    if market.supplies.get(ResourceType.FOOD, 0) > 0:
                        self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 10
                        market.supplies[ResourceType.FOOD] -= 1
                        events.append({
                            "type": "resource_gathered",
                            "data": {"resource": "food", "amount": 10, "source": "market"}
                        })
                        food_acquired = True
                        break
            if not food_acquired:
                events.append({
                    "type": "hunger_motivation",
                    "data": {"action": "seek_food", "hunger": self.needs.hunger, "reason": "no food available"}
                })

        elif action == "seek_water":
            events.append({
                "type": "thirst_motivation",
                "data": {"action": "seek_water", "thirst": self.needs.thirst}
            })

        elif action == "rest":
            self.needs.rest = min(1.0, self.needs.rest + 0.1)
            self.energy = min(1.0, self.energy + 0.1)
            self.health = min(1.0, self.health + 0.05)
            events.append({
                "type": "rested",
                "data": {"rest": self.needs.rest, "energy_after": self.energy, "health_after": self.health}
            })

        elif action == "trade":
            if target and target != "unknown":
                market = None
                for m in core.world.get("markets", []):
                    if m.id == target or m.regionId == target:
                        market = m
                        break
                if market:
                    food_price = market.prices.get("food", 1.0)
                    if self.inventory.resources.get("food", 0) > 0:
                        self.inventory.resources["food"] -= 1
                        self.needs.hunger = min(1.0, self.needs.hunger + 0.1)
                        self.health = min(1.0, self.health + 0.05)
                        events.append({"type": "traded", "data": {"action": "sell_food", "price": food_price}})
                    else:
                        self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 1
                        self.needs.hunger = max(0, self.needs.hunger - 0.01)
                        events.append({"type": "traded", "data": {"action": "buy_food", "price": food_price}})
                else:
                    events.append({"type": "hunger_motivation", "data": {"action": "trade", "reason": "no market"}})
            else:
                events.append({"type": "hunger_motivation", "data": {"action": "trade", "reason": "no target"}})

        elif action == "build":
            if target and target != "unknown":
                self.energy = max(0, self.energy - 0.2)
                events.append({"type": "build", "data": {"building_type": "farm", "location": target}})
            else:
                events.append({"type": "hunger_motivation", "data": {"action": "build", "reason": "no target"}})

        elif action == "gather_wood":
            self.inventory.resources["wood"] = self.inventory.resources.get("wood", 0) + 10
            events.append({
                "type": "resource_gathered",
                "data": {"resource": "wood", "amount": 10}
            })

        elif action == "gather_iron":
            self.inventory.resources["iron"] = self.inventory.resources.get("iron", 0) + 5
            events.append({
                "type": "resource_gathered",
                "data": {"resource": "iron", "amount": 5}
            })

        elif action == "gather_food":
            self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 15
            events.append({
                "type": "resource_gathered",
                "data": {"resource": "food", "amount": 15}
            })

        elif action == "socialize":
            if target and target != "unknown":
                self.needs.social = min(1.0, self.needs.social + 0.1)
                disposition = self.personality.disposition
                if disposition == "friendly":
                    weight = 0.3
                elif disposition == "hostile":
                    weight = -0.3
                else:
                    weight = 0.05
                self.relationships.values[target] = round(
                    self.relationships.values.get(target, 0.0) + weight, 2
                )
                self.memory.add_social(
                    related_agent_id=target,
                    content={"action": "socialize", "target": target, "weight": weight},
                    emotional_weight=weight
                )
                events.append({
                    "type": "social_interaction",
                    "data": {
                        "action": "socialize",
                        "target": target,
                        "relationship_value": self.relationships.values[target],
                        "social_need_after": self.needs.social
                    }
                })
            else:
                events.append({
                    "type": "social_interaction",
                    "data": {"action": "socialize", "target": "none", "reason": "no nearby agents"}
                })

        elif action == "explore":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            new_x = max(0, min(core.config.width - 1, self.position.x + dx))
            new_y = max(0, min(core.config.height - 1, self.position.y + dy))
            self.position.x = new_x
            self.position.y = new_y
            self.energy = max(0, self.energy - 0.05)
            self.needs.safety = max(0, self.needs.safety - 0.01)
            events.append({
                "type": "moved",
                "data": {"x": self.position.x, "y": self.position.y, "dx": dx, "dy": dy,
                         "energy_after": self.energy}
            })

        elif action == "eat":
            food_amount = self.inventory.resources.get("food", 0)
            if food_amount > 0:
                self.inventory.resources["food"] = food_amount - 1
                self.needs.hunger = min(1.0, self.needs.hunger + 0.2)
                self.health = min(1.0, self.health + 0.1)
                self.energy = min(1.0, self.energy + 0.05)
                events.append({
                    "type": "fed",
                    "data": {"food_consumed": 1, "hunger_after": self.needs.hunger,
                             "health_after": self.health, "energy_after": self.energy}
                })
            else:
                food_acquired = False
                for res in core.world.get("resources", []):
                    if res.type == ResourceType.FOOD and res.amount > 0:
                        self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 15
                        res.amount -= 1
                        events.append({
                            "type": "resource_gathered",
                            "data": {"resource": "food", "amount": 15, "reason": "eat_redirect"}
                        })
                        food_acquired = True
                        break
                if not food_acquired:
                    for market in core.world.get("markets", []):
                        if market.supplies.get(ResourceType.FOOD, 0) > 0:
                            self.inventory.resources["food"] = self.inventory.resources.get("food", 0) + 10
                            market.supplies[ResourceType.FOOD] -= 1
                            events.append({
                                "type": "resource_gathered",
                                "data": {"resource": "food", "amount": 10, "source": "market", "reason": "eat_redirect"}
                            })
                            food_acquired = True
                            break
                if not food_acquired:
                    events.append({
                        "type": "hunger_motivation",
                        "data": {"action": "eat", "reason": "no food available anywhere"}
                    })

        elif action == "form_organization":
            org_id = f"org-{self.id}-{int(time.time()*1000)}"
            self.organization = org_id
            events.append({
                "type": "organization_formed",
                "data": {"organization_id": org_id, "leader": self.id, "name": f"{self.id}-guild"}
            })
            self.memory.add_episodic(content={"action": "form_organization", "org_id": org_id})

        elif action == "join_organization":
            if target and target != "unknown":
                self.organization = target
                events.append({
                    "type": "joined_organization",
                    "data": {"organization_id": target, "member": self.id}
                })
                self.memory.add_episodic(content={"action": "join_organization", "org_id": target})
            else:
                events.append({
                    "type": "hunger_motivation",
                    "data": {"action": "join_organization", "reason": "no organization to join"}
                })

        return events

    def update_memory(self, event: dict, core):
        event_type = event.get("type", "")
        data = event.get("data", {})
        salience = self._compute_salience(event_type, data)
        self.memory.add_episodic(content=event, source_event_id=event.get("id", ""))
        for mem in self.memory.episodic:
            if mem.content == event:
                mem.emotional_weight = salience
                break
        if len(self.memory.episodic) > 10:
            self.memory.consolidate()

    def _compute_salience(self, event_type: str, data: dict) -> float:
        base_salience = 0.5
        critical_types = {"death", "conflict", "famine", "mine_collapse", "flood"}
        if event_type in critical_types:
            return min(1.0, base_salience + 0.4)
        need_types = {"hunger_motivation", "thirst_motivation", "need_decay"}
        if event_type in need_types:
            return 0.6
        resource_types = {"resource_growth", "resource_depleted"}
        if event_type in resource_types:
            return 0.5
        if event_type == "social_interaction":
            emotional_weight = data.get("emotional_weight", 0.5)
            return emotional_weight
        return base_salience