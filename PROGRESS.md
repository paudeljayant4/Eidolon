# Eidolon Progress Log

## Stage 1: Monorepo & Infrastructure ✅
**Built:**
- Root `package.json` with workspaces for frontend, backend, simulation, agents, shared
- `frontend/` - Next.js + TypeScript + Tailwind + React Three Fiber
- `backend/` - FastAPI + Python with PostgreSQL + Redis
- `simulation/` - Core deterministic engine (importable package)
- `agents/` - Cognition layer package
- `shared/` - Shared types/schemas package
- Docker Compose for local dev (db, redis, backend, frontend)
- GitHub Actions CI (lint, typecheck, unit tests, smoke test)
- `docs/DEVELOPMENT.md` with local development instructions

**Deferred:**
- Full CI test configuration (placeholder scripts)

**Next:** Stage 2 - World model

---

## Stage 2: World Model ✅
**Built:**
- Shared TypeScript types: TerrainType, ResourceType, BuildingType, Position, Region, City, Building, Resource, Agent, Market, Event, EventType, Personality, Needs, Skills, Inventory, Relationships, Organization
- Python types in `simulation/_types.py` with dataclasses for all entities
- World generation: 10×10 grid with procedural terrain (forest, mountain, desert, river, plains, city, ocean)
- Resource distribution: wood, stone, iron, food, water based on terrain
- City generation from regions with appropriate buildings
- Market initialization per region
- Agent creation at world center

**Deferred:**
- Full 100×100+ scalability testing

**Next:** Stage 3 - Deterministic simulation engine

---

## Stage 3: Deterministic Simulation Engine ✅
**Built:**
- Tick-based core loop with `tick_step()` method
- Event-sourced `EventLog` class recording all state changes
- Deterministic seeding via `WorldConfig.seed`
- Save/load via pickle (world state + event log)
- Pause/resume functionality
- Replay system that reconstructs world state at any past tick from event log
- Event handlers for: resource_growth, price_changed, moved, rested, need_decay
- Deterministic RNG with `deterministic_random()`

**Verified:**
- Multi-tick simulation runs correctly (99 → 98 → 97 → 97 → 95 events over 5 ticks)
- Save/load preserves state across restarts
- Pause correctly stops tick processing
- Replay at tick 0, 3, 5 all produce consistent world states
- Same seed + same inputs produces reproducible event types

**Deferred:**
- Full event handler coverage (currently covers core need/resource events)

**Next:** Stage 4 - Agent cognitive architecture

---

## Stage 4: Agent Cognitive Architecture ✅
**Built:**
- Three-tier memory system (episodic, semantic, social) with emotional salience weighting
- Agent pipeline: Perception → World Model → Memory → Planner → Decision → Action
- RuleBasedPlanner: utility-AI fallback for large-population affordable runs
- LLMBasedPlanner: tool-calling LLM-backed planner with embeddings + vector DB integration points
- Agent memory with salience-based retention and periodic consolidation pass
- Both agent types selectable per-agent (AgentType enum: RULE_BASED, LLM_BACKED)
- Memory consolidation: promotes high-salience episodic → semantic memories

**Verified:**
- Agent perception correctly extracts resources and market prices from world state
- Rule-based planner: hungry agent → seek_food, satiated agent → explore
- Agent actions produce correct events (hunger_motivation, moved, etc.)
- Memory system records episodic memories with emotional salience weighting
- Consolidation pass promotes important memories to semantic tier
- Deterministic behavior: same seed produces reproducible agent decisions
- **Cycle 1 fix: added `eat` action; final_hunger goes from 0 → 0.6 when food available**

**Deferred:**
- Full LLM integration (tool-calling against real provider)
- Vector DB for semantic memory retrieval
- Full social memory system with relationship tracking

**Next:** Stage 5 - Economy (buy/sell/trade/invest/borrow/save/produce/consume)

## Cycle 1: Correctness � Agent Hunger Starvation (Feb 2026)

### Observed Problem
In a deterministic 100-tick simulation (seed=42, 10x10 world), agents consistently
have their hunger need decay to 0 and remain there indefinitely. While agents can
gather_food (adding food to their inventory), there is no mechanism to convert
inventory food into hunger restoration.

### Evidence
| Metric | Value (before fix) | Value (after fix) |
|--------|-------------------|-------------------|
| final_hunger | 0 | 0.6 |
| hunger_min | 0 | 0.5 |
| hunger_max | ~0 | 0.99 |
| final_food_inventory | unconsumed | 2 |
| events_per_tick | 58.84 | 58.34 |

### Fix
Added eat action to Agent.act() in agents/_agent.py:
- Consumes 1 food from inventory when action == eat
- Restores hunger: needs.hunger = min(1.0, needs.hunger + 0.2)
- Emits fed event with data

Also added eat priority in RuleBasedPlanner.plan():
- If agent has food in inventory and hunger < 0.7, choose eat

### Verification
- Determinism: Two runs with seed=42 produce identical results
  (final_hunger=0.6, final_food=2, same event counts)
- Regression test: test_agent_can_restore_hunger_by_eating() passes
- Before/after: final_hunger goes from 0 to 0.6

### Files Changed
- agents/_agent.py added eat action branch + planner priority
- PROGRESS.md documented cycle outcome
- docs/issues/Cycle1-correctness-hunger-starvation.md full issue record

### Category Rotation
Next cycle will focus on emergent depth � checking that agents form
meaningful relationships, conflicts, and guilds beyond basic need satisfaction.
