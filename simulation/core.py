import json
import pickle
import random
from datetime import datetime
from ._types import (
    WorldConfig, Position, Region, Building, BuildingType, Resource,
    ResourceType, Agent, AgentId, Market, Event, EventType,
    Needs, Personality, Skills, Inventory, Relationships, Organization,
)


class EventLog:
    """Event-sourced log that records all state changes."""
    
    MAX_EVENTS = 100000  # Bounded event log to prevent memory leak
    
    def __init__(self):
        self.events: list[Event] = []
        self._event_count = 0
    
    def emit(self, event_type: str, source: str | None, target: str | None, data: dict | None = None) -> Event:
        """Emit an event and return it."""
        event_id = f"evt-{self._event_count:010d}"
        self._event_count += 1
        event = Event(
            id=event_id,
            timestamp=datetime.now().timestamp(),
            type=event_type,
            source=source,
            target=target,
            data=data or {}
        )
        self.events.append(event)
        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS:]
        return event

    def get_events_by_type(self, event_type: str) -> list[Event]:
        return [e for e in self.events if e.type == event_type]

    def get_events_between(self, start_tick: int, end_tick: int) -> list[Event]:
        return [e for e in self.events if start_tick <= e.timestamp <= end_tick]

    def to_dict(self) -> dict:
        return {"events": [e.to_dict() for e in self.events]}

    @classmethod
    def from_dict(cls, data: dict) -> EventLog:
        log = cls()
        for e_data in data.get("events", []):
            event = Event(
                id=e_data["id"],
                timestamp=e_data["timestamp"],
                type=e_data["type"],
                source=e_data.get("source"),
                target=e_data.get("target"),
                data=e_data.get("data", {})
            )
            log.events.append(event)
            log._event_count += 1
        return log


class SimulationCore:
    """Deterministic tick-based simulation core."""
    
    def __init__(self, config: WorldConfig, seed: int | None = None):
        self.config = config
        self.seed = seed
        self.tick = 0
        self.world: dict | None = None
        self.event_log = EventLog()
        self.running = False
        self.paused = False
    
    def initialize(self) -> dict:
        """Initialize the world from config."""
        from .world_gen import generate_world
        self.world = generate_world(self.config)
        self.tick = 0
        self.event_log = EventLog()
        self.running = True
        self.paused = False
        return self.world
    
    def tick_step(self) -> list[Event]:
        """Execute one simulation tick. Returns events emitted this tick."""
        if not self.running or self.paused:
            return []
        
        events: list[Event] = []
        
        # 1. Process resource tick
        events.extend(self._process_resources())
        
        # 2. Process market price updates
        events.extend(self._update_markets())
        
        # 3. Agent actions
        events.extend(self._process_agents())
        
        # 4. Decay needs
        events.extend(self._decay_needs())
        
        # Set timestamp to current tick for deterministic replay
        for event in events:
            event.timestamp = float(self.tick)
        
        self.tick += 1
        return events
    
    def _process_resources(self) -> list[Event]:
        """Process resource production/consumption."""
        events = []
        if self.world is None:
            return events
        
        # Resource regeneration based on terrain (timer-based for performance)
        GROWTH_INTERVAL = 5  # regrow every 5 ticks
        
        for resource in self.world["resources"]:
            # Decrement timer each tick
            if resource.growth_timer > 0:
                resource.growth_timer -= 1
            
            # Only regrow when timer reaches 0
            if resource.growth_timer <= 0 and resource.amount < resource.maxAmount:
                resource.amount = min(resource.maxAmount, resource.amount + 1)
                resource.growth_timer = GROWTH_INTERVAL
                events.append(self.resource_event("resource_growth", resource.id, {
                    "type": resource.type.value,
                    "amount": resource.amount,
                    "max": resource.maxAmount
                }))
        
        return events
    
    def _update_markets(self) -> list[Event]:
        """Update market prices based on supply/demand."""
        events = []
        if self.world is None:
            return events
        
        for market in self.world["markets"]:
            # Compute price from supply and demand
            for res_type in ResourceType:
                supply = market.supplies.get(res_type, 0)
                demand = market.demands.get(res_type, 0)
                
                if demand > 0:
                    # Price increases with low supply, decreases with high demand
                    if supply < demand:
                        # Scarcity drives price up
                        market.prices[res_type] = min(10.0, market.prices.get(res_type, 1.0) * 1.1)
                    else:
                        # Abundance drives price down
                        market.prices[res_type] = max(0.1, market.prices.get(res_type, 1.0) * 0.99)
                    
                    events.append(self.market_event("price_changed", market.id, {
                        "resource": res_type.value,
                        "price": market.prices[res_type],
                        "supply": supply,
                        "demand": demand
                    }))
        
        return events
    
    def _process_agents(self) -> list[Event]:
        """Process agent actions for this tick."""
        events = []
        if self.world is None:
            return events
        
        agents = self.world.get("agents", [])
        primary_agent = self.world.get("agent", None)
        all_agents = agents if agents else ([primary_agent] if primary_agent else [])
        
        for agent in all_agents:
            if agent.needs.hunger < 0.5:
                events.append(self.agent_action_event("hunger_motivation", agent.id, {
                    "hunger": agent.needs.hunger,
                    "action": "seek_food"
                }))
            if agent.needs.thirst < 0.5:
                events.append(self.agent_action_event("thirst_motivation", agent.id, {
                    "thirst": agent.needs.thirst,
                    "action": "seek_water"
                }))
            if agent.needs.social < 0.3:
                events.append(self.agent_action_event("social_motivation", agent.id, {
                    "social": agent.needs.social,
                    "action": "socialize"
                }))
        
        return events
    
    def _decay_needs(self) -> list[Event]:
        """Decay agent needs over time."""
        events = []
        if self.world is None:
            return events
        
        agents = self.world.get("agents", [])
        primary_agent = self.world.get("agent", None)
        all_agents = agents if agents else ([primary_agent] if primary_agent else [])
        
        for agent in all_agents:
            agent.needs.hunger = max(0, agent.needs.hunger - 0.01)
            agent.needs.thirst = max(0, agent.needs.thirst - 0.01)
            agent.needs.rest = max(0, agent.needs.rest - 0.005)
            agent.needs.social = max(0, agent.needs.social - 0.002)
            agent.needs.safety = max(0, agent.needs.safety - 0.001)
            agent.health = max(0, agent.health - 0.002)
            agent.energy = max(0, agent.energy - 0.005)

            events.append(self.agent_action_event("need_decay", agent.id, {
                "hunger": agent.needs.hunger,
                "thirst": agent.needs.thirst,
                "rest": agent.needs.rest,
                "social": agent.needs.social,
                "health": agent.health,
                "energy": agent.energy
            }))

        return events

    def agent_action(self, action: str, target: str | None = None, data: dict | None = None) -> list[Event]:
        """Execute an agent action and return events."""
        events = []
        
        if self.world is None:
            return events
        
        agent = self.world["agent"]
        
        if action == "move":
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            agent.position.x = max(0, min(self.config.width - 1, agent.position.x + dx))
            agent.position.y = max(0, min(self.config.height - 1, agent.position.y + dy))
            agent.energy = max(0, agent.energy - 0.05)
            
            events.append(self.agent_action_event("moved", agent.id, {
                "x": agent.position.x,
                "y": agent.position.y,
                "dx": dx,
                "dy": dy,
                "energy_after": agent.energy
            }))
        
        elif action == "trade":
            agent.energy = max(0, agent.energy - 0.1)
            events.append(self.agent_action_event("traded", agent.id, {
                "target": target,
                "data": data or {}
            }))
        
        elif action == "rest":
            agent.needs.rest = min(1.0, agent.needs.rest + 0.1)
            agent.energy = min(1.0, agent.energy + 0.1)
            agent.health = min(1.0, agent.health + 0.05)
            events.append(self.agent_action_event("rested", agent.id, {
                "rest": agent.needs.rest,
                "energy_after": agent.energy,
                "health_after": agent.health
            }))
        
        elif action == "build":
            agent.energy = max(0, agent.energy - 0.2)
            events.append(self.agent_action_event("build", agent.id, {
                "target": target
            }))
        
        elif action == "explore":
            agent.energy = max(0, agent.energy - 0.05)
            agent.needs.safety = max(0, agent.needs.safety - 0.01)
            events.append(self.agent_action_event("moved", agent.id, {
                "x": agent.position.x,
                "y": agent.position.y,
                "energy_after": agent.energy
            }))
        
        return events
    
    def pause(self):
        self.paused = True
    
    def resume(self):
        self.paused = False
    
    def save(self, path: str):
        """Save simulation state to file."""
        state = {
            "tick": self.tick,
            "world": self.world,
            "event_log": self.event_log.to_dict(),
            "running": self.running,
            "paused": self.paused
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
    
    def load(self, path: str):
        """Load simulation state from file."""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        self.tick = state["tick"]
        self.world = state["world"]
        self.event_log = EventLog.from_dict(state["event_log"])
        self.running = state.get("running", True)
        self.paused = state.get("paused", False)
    
    def replay_tick(self, target_tick: int) -> dict:
        """Reconstruct the world state at a given tick by replaying events.
        
        Returns the world state dict as it existed at target_tick.
        """
        if self.world is None:
            raise ValueError("World not initialized")
        
        if target_tick < 0 or target_tick > self.tick:
            raise ValueError(f"Invalid target tick: {target_tick}. "
                          f"Current tick is {self.tick}, max is {self.tick}")
        
        # Start with a fresh world from config
        from .world_gen import generate_world
        replayed_world = generate_world(self.config)
        
        # Apply each event up to target_tick
        for event in self.event_log.events:
            if event.timestamp > target_tick:
                break
            self._apply_event(replayed_world, event)
        
        return {
            "world": replayed_world,
            "replay_tick": target_tick,
            "events_applied": len([e for e in self.event_log.events if e.timestamp <= target_tick])
        }
    
    def _apply_event(self, world: dict, event: Event):
        """Apply a single event to the world state."""
        event_type = event.type
        data = event.data or {}
        
        if event_type == "resource_growth":
            self._handle_resource_growth(world, event, data)
        elif event_type == "price_changed":
            self._handle_price_changed(world, event, data)
        elif event_type == "hunger_motivation":
            self._handle_hunger_motivation(world, event, data)
        elif event_type == "thirst_motivation":
            self._handle_thirst_motivation(world, event, data)
        elif event_type == "moved":
            self._handle_moved(world, event, data)
        elif event_type == "traded":
            self._handle_traded(world, event, data)
        elif event_type == "rested":
            self._handle_rested(world, event, data)
        elif event_type == "need_decay":
            self._handle_need_decay(world, event, data)
        elif event_type == "social_interaction":
            self._handle_social_interaction(world, event, data)
        elif event_type == "fed":
            self._handle_fed(world, event, data)
        elif event_type == "resource_gathered":
            self._handle_resource_gathered(world, event, data)
        elif event_type == "organization_formed":
            self._handle_organization_formed(world, event, data)
        elif event_type == "joined_organization":
            self._handle_joined_organization(world, event, data)
        elif event_type == "birth":
            self._handle_birth(world, event, data)
        elif event_type == "death":
            self._handle_death(world, event, data)
        elif event_type == "conflict":
            self._handle_conflict(world, event, data)
        elif event_type == "build":
            self._handle_build(world, event, data)
        elif event_type == "research":
            self._handle_research(world, event, data)
        elif event_type == "resource_depletion":
            self._handle_resource_depletion(world, event, data)
        elif event_type == "election":
            self._handle_election(world, event, data)
        elif event_type == "treaty":
            self._handle_treaty(world, event, data)
        elif event_type == "war":
            self._handle_war(world, event, data)
        elif event_type == "mine_collapse":
            self._handle_mine_collapse(world, event, data)
        elif event_type == "flood":
            self._handle_flood(world, event, data)
        elif event_type == "famine":
            self._handle_famine(world, event, data)

    def _handle_resource_growth(self, world: dict, event: Event, data: dict):
        """Handle resource growth event."""
        resource_type = data.get("type")
        amount = data.get("amount")
        max_amount = data.get("max")
        for resource in world["resources"]:
            if resource.type.value == resource_type:
                resource.amount = min(max_amount, amount)
                break
    
    def _handle_price_changed(self, world: dict, event: Event, data: dict):
        """Handle market price change event."""
        resource = data.get("resource")
        price = data.get("price")
        for market in world["markets"]:
            market.prices[ResourceType(resource)] = price
            break
    
    def _handle_hunger_motivation(self, world: dict, event: Event, data: dict):
        """Handle hunger motivation event."""
        pass  # Agent action, state handled separately
    
    def _handle_thirst_motivation(self, world: dict, event: Event, data: dict):
        """Handle thirst motivation event."""
        pass  # Agent action, state handled separately
    
    def _handle_moved(self, world: dict, event: Event, data: dict):
        """Handle agent move event."""
        x = data.get("x")
        y = data.get("y")
        agent_id = event.source
        if "agents" in world:
            for agent in world["agents"]:
                if agent.id == agent_id:
                    agent.position.x = x
                    agent.position.y = y
                    break
        elif "agent" in world:
            world["agent"].position.x = x
            world["agent"].position.y = y
    
    def _handle_traded(self, world: dict, event: Event, data: dict):
        """Handle trade event."""
        pass  # Trade details in data
    
    def _handle_rested(self, world: dict, event: Event, data: dict):
        """Handle rest event."""
        rest = data.get("rest")
        world["agent"].needs.rest = rest
    
    def _handle_need_decay(self, world: dict, event: Event, data: dict):
        """Handle need decay event."""
        hunger = data.get("hunger")
        thirst = data.get("thirst")
        rest = data.get("rest")
        world["agent"].needs.hunger = hunger
        world["agent"].needs.thirst = thirst
        world["agent"].needs.rest = rest

    def _handle_social_interaction(self, world: dict, event: Event, data: dict):
        """Handle social interaction event."""
        agent_id = event.source
        target = data.get("target")
        agents = world.get("agents")
        if target and agents:
            for agent in agents:
                if agent.id == target:
                    relationship_val = data.get("relationship_value", 0.0)
                    agent.relationships.values[agent_id] = round(
                        agent.relationships.values.get(agent_id, 0.0) + relationship_val * 0.1, 2
                    )
                    break

    def _handle_fed(self, world: dict, event: Event, data: dict):
        """Handle fed event."""
        pass  # Agent state handled by Agent.act()

    def _handle_resource_gathered(self, world: dict, event: Event, data: dict):
        """Handle resource gathered event."""
        pass  # Resource state handled by Agent.act()

    def _handle_organization_formed(self, world: dict, event: Event, data: dict):
        """Handle organization formed event."""
        org_id = data.get("organization_id")
        org_name = data.get("name")
        leader = data.get("leader")
        if "organizations" not in world:
            world["organizations"] = []
        org = Organization(
            id=org_id, name=org_name, leader_id=leader, organization_type="guild"
        )
        world["organizations"].append(org)

    def _handle_joined_organization(self, world: dict, event: Event, data: dict):
        """Handle joined organization event."""
        org_id = data.get("organization_id")
        member = data.get("member")
        if "organizations" in world:
            for org in world["organizations"]:
                if org.id == org_id:
                    if member not in org.members:
                        org.members.append(member)
                    break

    def _handle_birth(self, world: dict, event: Event, data: dict):
        """Handle birth event — add new agent to world."""
        agent_data = data.get("agent")
        if agent_data and "agents" in world:
            from ._types import Agent, Position, Personality, Needs, Skills, Inventory, Relationships
            new_agent = Agent(
                id=agent_data.get("id", f"agent-{len(world['agents'])}"),
                position=Position(x=agent_data.get("x", 0), y=agent_data.get("y", 0)),
                personality=Personality(disposition=agent_data.get("disposition", "neutral")),
                needs=Needs(),
                skills=Skills(),
                inventory=Inventory(),
                relationships=Relationships(),
                health=1.0,
                energy=1.0
            )
            world["agents"].append(new_agent)

    def _handle_death(self, world: dict, event: Event, data: dict):
        """Handle death event — remove agent from world."""
        agent_id = data.get("agent_id")
        if agent_id and "agents" in world:
            world["agents"] = [a for a in world["agents"] if a.id != agent_id]

    def _handle_conflict(self, world: dict, event: Event, data: dict):
        """Handle conflict event — modify relationships and health."""
        agent_a = data.get("agent_a")
        agent_b = data.get("agent_b")
        damage = data.get("damage", 0.1)
        if agent_a and agent_b and "agents" in world:
            for a in world["agents"]:
                if a.id == agent_a:
                    a.health = max(0, a.health - damage)
                    if agent_b in a.relationships.values:
                        a.relationships.values[agent_b] = round(a.relationships.values[agent_b] - 0.2, 2)
                if a.id == agent_b:
                    a.health = max(0, a.health - damage)
                    if agent_a in a.relationships.values:
                        a.relationships.values[agent_a] = round(a.relationships.values[agent_a] - 0.2, 2)

    def _handle_build(self, world: dict, event: Event, data: dict):
        """Handle build event — add building to world."""
        from ._types import Building, BuildingType, Position
        building_data = data.get("building")
        if building_data and "buildings" not in world:
            world["buildings"] = []
        if building_data:
            b = Building(
                id=building_data.get("id", f"build-{len(world.get('buildings', []))}"),
                type=BuildingType(building_data.get("type", "farm")),
                regionId=building_data.get("region_id", ""),
                position=Position(x=building_data.get("x", 0), y=building_data.get("y", 0)),
                level=building_data.get("level", 1)
            )
            if "buildings" not in world:
                world["buildings"] = []
            world["buildings"].append(b)

    def _handle_research(self, world: dict, event: Event, data: dict):
        """Handle research event — advance technology."""
        tech = data.get("technology")
        if tech and "technologies" not in world:
            world["technologies"] = []
        if tech:
            if "technologies" not in world:
                world["technologies"] = []
            if tech not in world["technologies"]:
                world["technologies"].append(tech)

    def _handle_resource_depletion(self, world: dict, event: Event, data: dict):
        """Handle resource depletion event."""
        resource_id = data.get("resource_id")
        amount = data.get("amount", 1)
        if resource_id and "resources" in world:
            for res in world["resources"]:
                if res.id == resource_id:
                    res.amount = max(0, res.amount - amount)
                    break

    def _handle_election(self, world: dict, event: Event, data: dict):
        """Handle election event."""
        org_id = data.get("organization_id")
        winner = data.get("winner")
        if "organizations" in world:
            for org in world["organizations"]:
                if org.id == org_id:
                    org.leader_id = winner
                    break

    def _handle_treaty(self, world: dict, event: Event, data: dict):
        """Handle treaty event — modify relationships between organizations."""
        org_a = data.get("org_a")
        org_b = data.get("org_b")
        agreement = data.get("agreement", "alliance")
        if "organizations" in world:
            for org in world["organizations"]:
                if org.id == org_a:
                    org.resources["treaties"] = org.resources.get("treaties", []) + [org_b]
                if org.id == org_b:
                    org.resources["treaties"] = org.resources.get("treaties", []) + [org_a]

    def _handle_war(self, world: dict, event: Event, data: dict):
        """Handle war event — declare conflict between organizations."""
        org_a = data.get("org_a")
        org_b = data.get("org_b")
        if "organizations" in world:
            for org in world["organizations"]:
                if org.id == org_a:
                    org.resources["war"] = org_b
                if org.id == org_b:
                    org.resources["war"] = org_a

    def _handle_mine_collapse(self, world: dict, event: Event, data: dict):
        """Handle mine collapse event — damage building and deplete resource."""
        building_id = data.get("building_id")
        if building_id and "buildings" in world:
            for b in world["buildings"]:
                if b.id == building_id:
                    b.level = max(1, b.level - 1)
                    break
        resource_id = data.get("resource_id")
        if resource_id and "resources" in world:
            for res in world["resources"]:
                if res.id == resource_id:
                    res.amount = max(0, res.amount - 5)
                    break

    def _handle_flood(self, world: dict, event: Event, data: dict):
        """Handle flood event — damage resources and agents in region."""
        region_id = data.get("region_id")
        if region_id and "resources" in world:
            for res in world["resources"]:
                if res.regionId == region_id:
                    res.amount = max(0, res.amount - 3)
        if "agents" in world:
            for agent in world["agents"]:
                agent.needs.safety = max(0, agent.needs.safety - 0.2)
                agent.health = max(0, agent.health - 0.1)

    def _handle_famine(self, world: dict, event: Event, data: dict):
        """Handle famine event — deplete food resources and affect agents."""
        if "resources" in world:
            for res in world["resources"]:
                if res.type.value == "food":
                    res.amount = max(0, res.amount - 5)
        if "agents" in world:
            for agent in world["agents"]:
                agent.needs.hunger = min(1.0, agent.needs.hunger + 0.3)
                agent.health = max(0, agent.health - 0.1)

    # Event helper methods

    def resource_event(self, event_type: str, resource_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"resource-{resource_id}", None, data)
    
    def market_event(self, event_type: str, market_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"market-{market_id}", None, data)
    
    def agent_action_event(self, event_type: str, agent_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"agent-{agent_id}", None, data)


# For deterministic random with seed
_random_cache: dict[int, random.Random] = {}
_event_counter = 0

def deterministic_random(event_type: str, tick: int, seed: int | None = None) -> random.Random:
    """Get a deterministic RNG instance for a given type and tick.
    Cleans up old cache entries beyond the current tick window."""
    global _event_counter
    _event_counter += 1
    key = f"{event_type}-{tick}"
    if key not in _random_cache:
        _random_cache[key] = random.Random(seed or 42)
    # Clean up entries older than 1000 ticks to prevent memory leak
    if _event_counter % 1000 == 0:
        old_keys = [k for k in _random_cache if int(k.split("-")[-1]) < tick - 1000]
        for k in old_keys:
            del _random_cache[k]
    return _random_cache[key]