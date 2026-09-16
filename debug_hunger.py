"""Debug hunger decay."""
import sys
sys.path.insert(0, r'C:\stardance files\Eidolon')
from simulation.core import SimulationCore
from simulation._types import WorldConfig

core = SimulationCore(config=WorldConfig(width=20, height=20, seed=42), seed=42)
core.initialize()

for tick in range(20):
    events = core.tick_step()
    agent = core.world["agents"][0]
    print(f"Tick {tick}: hunger={agent.needs.hunger:.3f}, energy={agent.energy:.3f}, health={agent.health:.3f}")