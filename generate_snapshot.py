"""Generate a bounded simulation snapshot for the observer demo."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig
import json

core = SimulationCore(config=WorldConfig(width=10, height=10, seed=42), seed=42)
core.initialize()

events = []
agents_data = []
for tick in range(50):
    tick_events = core.tick_step()
    for e in tick_events:
        events.append({"tick": tick, "type": e.type, "data": e.data or {}})

agents_data = []
for a in core.world.get("agents", []):
    agents_data.append({"id": a.id, "hunger": round(a.needs.hunger, 3), "health": round(a.health, 3), "energy": round(a.energy, 3), "social": round(a.needs.social, 3)})

snapshot = {"tick": core.tick, "world_size": f"{core.config.width}x{core.config.height}", "seed": core.seed, "agents": agents_data, "events": events, "note": "Demo mode — bounded 50-tick simulation snapshot. Not a live backend."}
with open(r"C:\stardance files\Eidolon\frontend\public\simulation-snapshot.json", 'w') as f:
    json.dump(snapshot, f, indent=2)
print(f"Snapshot: {core.tick} ticks, {len(agents_data)} agents, {len(events)} events")
