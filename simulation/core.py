import json
import pickle
import random
from datetime import datetime
from uuid import uuid4
from ._types import (
    WorldConfig, Position, Region, Building, BuildingType, Resource,
    ResourceType, Agent, AgentId, Market, Event, EventType,
    Needs, Personality, Skills, Inventory, Relationships, Organization,
)


class EventLog:
    """Event-sourced log that records all state changes."""
    
    def __init__(self):
        self.events: list[Event] = []
    
    def emit(self, event_type: str, source: str | None, target: str | None, data: dict | None = None) -> Event:
        """Emit an event and return it."""
        event = Event(
            id=str(uuid4()),
            timestamp=datetime.now().timestamp(),
            type=event_type,
            source=source,
            target=target,
            data=data or {}
        )
        self.events.append(event)
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
        
            events.append(self.agent_action_event("need_decay", agent.id, {
                "hunger": agent.needs.hunger,
                "thirst": agent.needs.thirst,
                "rest": agent.needs.rest,
                "social": agent.needs.social
            }))
        
        return events
    
    def agent_action(self, action: str, target: str | None = None, data: dict | None = None) -> list[Event]:
        """Execute an agent action and return events."""
        events = []
        
        if self.world is None:
            return events
        
        agent = self.world["agent"]
        
        if action == "move":
            # Move agent randomly
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            agent.position.x = max(0, min(self.config.width - 1, agent.position.x + dx))
            agent.position.y = max(0, min(self.config.height - 1, agent.position.y + dy))
            
            events.append(self.agent_action_event("moved", agent.id, {
                "x": agent.position.x,
                "y": agent.position.y,
                "dx": dx,
                "dy": dy
            }))
        
        elif action == "trade":
            events.append(self.agent_action_event("traded", agent.id, {
                "target": target,
                "data": data or {}
            }))
        
        elif action == "rest":
            agent.needs.rest = min(1.0, agent.needs.rest + 0.1)
            events.append(self.agent_action_event("rested", agent.id, {
                "rest": agent.needs.rest
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
        if target and "agents" in world:
            for agent in world["agents"]:
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

    # Event helper methods

    def resource_event(self, event_type: str, resource_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"resource-{resource_id}", None, data)
    
    def market_event(self, event_type: str, market_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"market-{market_id}", None, data)
    
    def agent_action_event(self, event_type: str, agent_id: str, data: dict) -> Event:
        return self.event_log.emit(event_type, f"agent-{agent_id}", None, data)


# For deterministic random with seed
_random_cache: dict[int, random.Random] = {}

def deterministic_random(event_type: str, tick: int, seed: int | None = None) -> random.Random:
    """Get a deterministic RNG instance for a given type and tick."""
    key = f"{event_type}-{tick}"
    if key not in _random_cache:
        _random_cache[key] = random.Random(seed or 42)
    return _random_cache[key]