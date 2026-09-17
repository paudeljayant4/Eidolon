# Eidolon

Deterministic AI simulation engine where agents autonomously navigate a procedural world — eating, drinking, trading, building, socializing, and forming organizations. Fully reproducible from seed.

## Live Demo

**[Observer Dashboard](https://paudeljayant4.github.io/Eidolon/)** — static snapshot of a 200-tick simulation showing agent states, events, buildings, and organizations.

## Architecture

```
eidolon/
├── simulation/          Core deterministic engine (Python)
├── agents/              Agent cognition & behavior (Python)
├── frontend/            Observer dashboard (Next.js + Three.js)
├── backend/             API server (FastAPI)
├── shared/              Shared types & schemas
├── docs/                Documentation & deployed observer
└── .github/             CI/CD workflows
```

**Engine loop:** Seed → World generation → Tick-based simulation → Event log → Save/Load/Replay

## Quick Start

### Run the simulation
```bash
cd simulation
python -c "
from core import SimulationCore
from _types import WorldConfig
core = SimulationCore(WorldConfig(width=10, height=10, seed=42), seed=42)
core.initialize()
for _ in range(100):
    core.tick_step()
print(f'Simulated {core.tick} ticks, {len(core.event_log.events)} events')
"
```

### Run tests
```bash
pytest test_agent_eat.py test_emergent_depth.py -v
```

### Generate observer snapshot
```bash
python generate_snapshot.py
```

### Frontend (dev)
```bash
cd frontend && npm install && npm run dev
```

### Docker Compose (full stack)
```bash
docker compose up --build
```

## Key Features

- **Deterministic** — same seed produces identical world and events every time
- **Emergent behavior** — agents form organizations, trade resources, build structures through simple priority-based decisions
- **Event-sourced** — every state change recorded; full replay from any point
- **Save/Load** — pickle-based serialization of complete world state
- **Visibility radius** — agents only perceive nearby resources and entities
- **Organization system** — agents autonomously join and form organizations

## Simulation Stats (200 ticks, 10×10 world)

| Metric | Value |
|--------|-------|
| Agents | 5 |
| Trades | ~500 |
| Builds | ~40 |
| Org joins | ~19 |
| Regeneration | 180% water, 54% food |

## Observer Dashboard

The deployed observer reads `simulation-snapshot.json` and displays:
- Agent states with need bars (hunger, thirst, energy, health, social)
- Event timeline and breakdown by type
- Building inventory
- Organization membership

## License

Private — not licensed for distribution.
