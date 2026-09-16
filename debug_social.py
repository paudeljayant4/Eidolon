"""Debug planner decisions at later ticks."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig, ResourceType

core = SimulationCore(config=WorldConfig(width=20, height=20, seed=42), seed=42)
core.initialize()

# Add market supplies/demands
for market in core.world.get("markets", []):
    market.supplies[ResourceType.FOOD] = 50
    market.demands[ResourceType.FOOD] = 30
    market.supplies[ResourceType.WOOD] = 20
    market.demands[ResourceType.WOOD] = 15

for tick in range(300):
    # Manually check planner decision before tick
    agent = core.world["agents"][0]
    perception = agent.perceive(core.world)
    needs = {
        "hunger": agent.needs.hunger,
        "thirst": agent.needs.thirst,
        "rest": agent.needs.rest,
        "social": agent.needs.social,
        "safety": agent.needs.safety,
        "energy": agent.energy,
        "inventory_food": agent.inventory.resources.get("food", 0),
        "inventory_water": agent.inventory.resources.get("water", 0),
        "inventory_wood": agent.inventory.resources.get("wood", 0),
        "inventory_iron": agent.inventory.resources.get("iron", 0),
    }
    
    from agents._agent import RuleBasedPlanner
    planner = RuleBasedPlanner()
    decision = planner.plan(perception, agent.memory, needs)
    
    events = core.tick_step()
    agent_actions = [e for e in events if e.source and e.source.startswith('agent-') and e.type not in ('need_decay', 'moved', 'rested')]
    if decision.action == "socialize":
        print(f"Tick {tick}: planner=socialize, hunger={agent.needs.hunger:.2f}, social={agent.needs.social:.2f}, rest={agent.needs.rest:.2f}, energy={agent.energy:.2f}, wood={agent.inventory.resources.get('wood',0)}")
    elif agent_actions:
        print(f"Tick {tick}: planner={decision.action}, actual={[f'{e.type}({e.source})' for e in agent_actions]}, hunger={agent.needs.hunger:.2f}, social={agent.needs.social:.2f}, rest={agent.needs.rest:.2f}, energy={agent.energy:.2f}, wood={agent.inventory.resources.get('wood',0)}")
    elif tick % 50 == 0:
        print(f"Tick {tick}: planner={decision.action}, hunger={agent.needs.hunger:.2f}, social={agent.needs.social:.2f}, rest={agent.needs.rest:.2f}, energy={agent.energy:.2f}, wood={agent.inventory.resources.get('wood',0)}")