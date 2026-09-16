"""Debug script to see what planner sees."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig
from agents._agent import RuleBasedPlanner, Agent, AgentType, Needs, Personality, Position, Skills, Inventory, Relationships
from simulation._types import ResourceType, Market

core = SimulationCore(config=WorldConfig(width=20, height=20, seed=42), seed=42)
core.initialize()

# Add some market supplies/demands
for market in core.world.get("markets", []):
    market.supplies[ResourceType.FOOD] = 100
    market.demands[ResourceType.FOOD] = 50
    market.supplies[ResourceType.WOOD] = 50
    market.demands[ResourceType.WOOD] = 20
    market.supplies[ResourceType.IRON] = 30
    market.demands[ResourceType.IRON] = 10

# Check market prices after one tick
events = core.tick_step()
print("After first tick (with market updates):")
for m in core.world.get("markets", [])[:3]:
    print(f"  {m.id}: food={m.prices.get('food',0):.2f}, wood={m.prices.get('wood',0):.2f}, iron={m.prices.get('iron',0):.2f}")

# Now test what an agent perceives
agent = core.world["agents"][0]
perception = agent.perceive(core.world)
print(f"\nAgent perception:")
print(f"  visible_resources: {perception.visible_resources}")
print(f"  market_prices: {perception.market_prices}")
print(f"  nearby_agents: {perception.nearby_agents}")

needs = {
    "hunger": agent.needs.hunger,
    "thirst": agent.needs.thirst,
    "rest": agent.needs.rest,
    "social": agent.needs.social,
    "safety": agent.needs.social,
    "inventory_food": agent.inventory.resources.get("food", 0),
    "inventory_water": agent.inventory.resources.get("water", 0),
    "inventory_wood": agent.inventory.resources.get("wood", 0),
    "inventory_iron": agent.inventory.resources.get("iron", 0),
}
print(f"\nNeeds: {needs}")

planner = RuleBasedPlanner()
decision = planner.plan(perception, agent.memory, needs)
print(f"\nPlanner decision: action={decision.action}, target={decision.target}, priority={decision.priority}")

# Now run a few ticks and see what happens
for tick in range(30):
    events = core.tick_step()
    agent_actions = [e for e in events if e.source and e.source.startswith('agent-') and e.type not in ('need_decay', 'moved')]
    if agent_actions:
        print(f"Tick {tick}: {[f'{e.type}({e.source})' for e in agent_actions]}")

print("\nFinal agent states:")
for a in core.world.get("agents", []):
    print(f"  {a.id}: hunger={a.needs.hunger:.2f}, energy={a.energy:.2f}, social={a.needs.social:.2f}, pos=({a.position.x},{a.position.y}), food={a.inventory.resources.get('food',0)}, wood={a.inventory.resources.get('wood',0)}, iron={a.inventory.resources.get('iron',0)}")