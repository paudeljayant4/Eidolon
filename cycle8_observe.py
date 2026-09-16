"""Cycle 8 observation script - run 500 ticks and capture emergent metrics."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig
import json

core = SimulationCore(config=WorldConfig(width=20, height=20, seed=42), seed=42)
core.initialize()

# Track metrics per tick
metrics = {
    "tick": [],
    "trade_events": [],
    "socialize_events": [],
    "build_events": [],
    "building_production_events": [],
    "org_count": [],
    "agent_hunger_avg": [],
    "agent_health_avg": [],
    "agent_energy_avg": [],
    "agent_social_avg": [],
    "food_total": [],
    "water_total": [],
    "wood_total": [],
    "iron_total": [],
    "stone_total": [],
    "trade_partners": [],  # unique (source, target) pairs
    "social_partners": [],  # unique (source, target) pairs
    "org_memberships": [],  # dict of org -> member count
}

trade_pairs = set()
social_pairs = set()

for tick in range(500):
    events = core.tick_step()
    
    # Count events
    trade_count = sum(1 for e in events if e.type == "traded")
    socialize_count = sum(1 for e in events if e.type == "social_interaction" and e.data.get("action") == "socialize")
    build_count = sum(1 for e in events if e.type == "build")
    prod_count = sum(1 for e in events if e.type == "building_production")
    
    # Track trade partners
    for e in events:
        if e.type == "traded" and e.source and e.target:
            trade_pairs.add((e.source, e.target))
        if e.type == "social_interaction" and e.data.get("action") == "socialize" and e.source and e.data.get("target"):
            social_pairs.add((e.source, e.data["target"]))
    
    # Agent stats
    agents = core.world.get("agents", [])
    if agents:
        hunger_avg = sum(a.needs.hunger for a in agents) / len(agents)
        health_avg = sum(a.health for a in agents) / len(agents)
        energy_avg = sum(a.energy for a in agents) / len(agents)
        social_avg = sum(a.needs.social for a in agents) / len(agents)
    else:
        hunger_avg = health_avg = energy_avg = social_avg = 0
    
    # Resource totals
    resources = core.world.get("resources", [])
    food_total = sum(r.amount for r in resources if r.type.value == "food")
    water_total = sum(r.amount for r in resources if r.type.value == "water")
    wood_total = sum(r.amount for r in resources if r.type.value == "wood")
    iron_total = sum(r.amount for r in resources if r.type.value == "iron")
    stone_total = sum(r.amount for r in resources if r.type.value == "stone")
    
    # Org memberships
    orgs = core.world.get("organizations", [])
    org_memberships = {o.id: len(o.members) for o in orgs}
    
    metrics["tick"].append(tick)
    metrics["trade_events"].append(trade_count)
    metrics["socialize_events"].append(socialize_count)
    metrics["build_events"].append(build_count)
    metrics["building_production_events"].append(prod_count)
    metrics["org_count"].append(len(orgs))
    metrics["agent_hunger_avg"].append(round(hunger_avg, 3))
    metrics["agent_health_avg"].append(round(health_avg, 3))
    metrics["agent_energy_avg"].append(round(energy_avg, 3))
    metrics["agent_social_avg"].append(round(social_avg, 3))
    metrics["food_total"].append(food_total)
    metrics["water_total"].append(water_total)
    metrics["wood_total"].append(wood_total)
    metrics["iron_total"].append(iron_total)
    metrics["stone_total"].append(stone_total)
    metrics["trade_partners"].append(len(trade_pairs))
    metrics["social_partners"].append(len(social_pairs))
    metrics["org_memberships"].append(org_memberships)

# Summary
print("=== CYCLE 8 OBSERVATION SUMMARY ===")
print(f"Ticks: 500")
print(f"Total trade events: {sum(metrics['trade_events'])}")
print(f"Total socialize events: {sum(metrics['socialize_events'])}")
print(f"Total build events: {sum(metrics['build_events'])}")
print(f"Total building_production events: {sum(metrics['building_production_events'])}")
print(f"Unique trade pairs: {metrics['trade_partners'][-1]}")
print(f"Unique social pairs: {metrics['social_partners'][-1]}")
print(f"Final orgs: {metrics['org_count'][-1]}")
print(f"Final org memberships: {metrics['org_memberships'][-1]}")
print()
print("Resource trends (first 10, last 10):")
print(f"  Food:   {metrics['food_total'][:5]} ... {metrics['food_total'][-5:]}")
print(f"  Water:  {metrics['water_total'][:5]} ... {metrics['water_total'][-5:]}")
print(f"  Wood:   {metrics['wood_total'][:5]} ... {metrics['wood_total'][-5:]}")
print(f"  Iron:   {metrics['iron_total'][:5]} ... {metrics['iron_total'][-5:]}")
print(f"  Stone:  {metrics['stone_total'][:5]} ... {metrics['stone_total'][-5:]}")
print()
print("Agent needs (first 10, last 10):")
print(f"  Hunger: {metrics['agent_hunger_avg'][:5]} ... {metrics['agent_hunger_avg'][-5:]}")
print(f"  Health: {metrics['agent_health_avg'][:5]} ... {metrics['agent_health_avg'][-5:]}")
print(f"  Energy: {metrics['agent_energy_avg'][:5]} ... {metrics['agent_energy_avg'][-5:]}")
print(f"  Social: {metrics['agent_social_avg'][:5]} ... {metrics['agent_social_avg'][-5:]}")
print()
print("Trade events per 50-tick window:")
for i in range(0, 500, 50):
    window = metrics['trade_events'][i:i+50]
    print(f"  {i}-{i+49}: {sum(window)}")
print()
print("Socialize events per 50-tick window:")
for i in range(0, 500, 50):
    window = metrics['socialize_events'][i:i+50]
    print(f"  {i}-{i+49}: {sum(window)}")

# Save full metrics
with open(r'C:\stardance files\Eidolon\cycle8_observation.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print("\nFull metrics saved to cycle8_observation.json")