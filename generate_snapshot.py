"""Generate a fresh simulation-snapshot.json for the observer."""
import sys, json
sys.path.insert(0, r"C:\stardance files\Eidolon")

from simulation.core import SimulationCore
from simulation._types import WorldConfig

core = SimulationCore(WorldConfig(width=10, height=10, seed=42), seed=42)
core.initialize()

# Run 200 ticks
for _ in range(200):
    core.tick_step()

world = core.world
agents = world.get("agents", [])
events = core.event_log.events

# Build snapshot
snapshot = {
    "tick": core.tick,
    "world_size": "10x10",
    "seed": 42,
    "agents": [],
    "buildings": [],
    "organizations": [],
    "events": [],
}

for a in agents:
    snapshot["agents"].append({
        "id": a.id,
        "hunger": round(a.needs.hunger, 3),
        "thirst": round(a.needs.thirst, 3),
        "energy": round(a.energy, 3),
        "health": round(a.health, 3),
        "social": round(a.needs.social, 3),
        "food_inv": a.inventory.resources.get("food", 0),
        "water_inv": a.inventory.resources.get("water", 0),
        "wood_inv": a.inventory.resources.get("wood", 0),
        "iron_inv": a.inventory.resources.get("iron", 0),
        "org": a.organization,
    })

for b in world.get("buildings", []):
    snapshot["buildings"].append({
        "id": b.id,
        "type": b.type.value if hasattr(b.type, 'value') else str(b.type),
        "regionId": b.regionId,
        "level": b.level,
    })

for o in world.get("organizations", []):
    snapshot["organizations"].append({
        "id": o.id,
        "name": o.name,
        "leader_id": o.leader_id,
        "members": o.members,
    })

# Bounded event log (last 500 events to keep file reasonable)
for e in events[-500:]:
    snapshot["events"].append({
        "id": e.id,
        "tick": int(e.timestamp),
        "type": e.type,
        "source": e.source,
        "target": e.target,
        "data": e.data,
    })

output_path = r"C:\stardance files\Eidolon\frontend\public\simulation-snapshot.json"
with open(output_path, "w") as f:
    json.dump(snapshot, f, indent=2, default=str)

print(f"Snapshot written: {len(snapshot['agents'])} agents, {len(snapshot['buildings'])} buildings, {len(snapshot['organizations'])} orgs, {len(snapshot['events'])} events")
