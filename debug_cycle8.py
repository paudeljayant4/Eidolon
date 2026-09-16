"""Debug script to see what actions agents take."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig

core = SimulationCore(config=WorldConfig(width=20, height=20, seed=42), seed=42)
core.initialize()

for tick in range(20):
    events = core.tick_step()
    agent_actions = [e for e in events if e.source and e.source.startswith('agent-')]
    if agent_actions:
        print(f"Tick {tick}: {[f'{e.type}({e.source})' for e in agent_actions]}")

print("\nFinal agent states:")
for a in core.world.get("agents", []):
    print(f"  {a.id}: hunger={a.needs.hunger:.2f}, energy={a.energy:.2f}, social={a.needs.social:.2f}, pos=({a.position.x},{a.position.y}), food_inv={a.inventory.resources.get('food',0)}, wood={a.inventory.resources.get('wood',0)}, iron={a.inventory.resources.get('iron',0)}")

print("\nMarket prices:")
for m in core.world.get("markets", [])[:3]:
    print(f"  {m.id}: food={m.prices.get('food',0):.2f}")

print("\nResources (food, water):")
food_res = [r for r in core.world['resources'] if r.type.value == 'food']
water_res = [r for r in core.world['resources'] if r.type.value == 'water']
print(f"  Food resources: {len(food_res)}, total={sum(r.amount for r in food_res)}")
print(f"  Water resources: {len(water_res)}, total={sum(r.amount for r in water_res)}")