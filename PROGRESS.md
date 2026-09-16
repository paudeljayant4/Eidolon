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

---

## Cycle 2: Correctness � No Food When Hunger is Critical (Feb 2026)

### Observed Problem
In the same deterministic 100-tick simulation (seed=42, 10x10 world), after the
Cycle 1 fix that added the `eat` action, a new gap was exposed: when hunger is
critical (< 0.3) and the agent's inventory has **zero food**, the `eat` action
did not define any acquisition behavior. The agent emitted a `hunger_motivation`
event but took no action to acquire food — it simply continued to starve.

The `seek_food` action in `Agent.act()` only emitted a `hunger_motivation` event
but never actually acquired food from visible resources or the market.

### Evidence (100 ticks, seed=42)
| Metric | Value (before fix) | Value (after fix) |
|--------|-------------------|-------------------|
| final_hunger | 0 | 0.8 |
| hunger_min | 0 | 0.2 |
| hunger_max | 0.19 | 0.8 |
| hunger_motivation_events | 100 | 0 |
| resource_gathered_events | 0 | 97 |
| final_food_inventory | 0 | 1452 |
| fed_events | 0 | 3 |

### Fix
1. **Modified `Agent.act("seek_food")`** to actually acquire food from visible resources
   - Checks `core.world["resources"]` for food with amount > 0
   - If found: gathers food (+15 to inventory), decrements resource
   - If not found: checks market for food supplies
   - If market has food: buys food (+10 to inventory), decrements supply
   - If neither: emits `hunger_motivation` with reason "no food available"

2. **Modified `Agent.act("eat")` else branch** to redirect to food acquisition
   - Instead of just emitting `hunger_motivation`, attempts to acquire food
   - Same logic as `seek_food`: resources → market → hunger_motivation

3. **Restructured `RuleBasedPlanner.plan()`** to fix priority ordering
   - **Priority 1**: Eat if inventory_food > 0 and hunger < 0.7 (takes precedence)
   - **Priority 2**: Seek food if hunger < 0.3 (only when no food to eat)
   - Previously the eat/explore check at the end overrode the seek_food decision
   - Also fixed: planner now correctly chooses `seek_food` when hunger < 0.3

### Decision
**Selected: Approach A** — The agent should interrupt its current plan to go acquire food.
When hunger is critical and inventory has zero food, the agent actively seeks to
acquire food from visible resources or the market.

### Hunger Thresholds (ARBITRARY TUNING CONSTANTS — flagged)
- `HUNGER_CRITICAL` = 0.3 (triggers seek_food planning)
- `HUNGER_EAT_THRESHOLD` = 0.7 (triggers eat planning when food available)
- `HUNGER_RESTORE_AMOUNT` = 0.2 (hunger restored per food consumed)
- `HUNGER_DECAY_RATE` = 0.01 (hunger decay per tick)
- `FOOD_GATHER_AMOUNT` = 15 (food gained per gather action)
- `FOOD_CONSUME_AMOUNT` = 1 (food consumed per eat action)

### Verification
- **10 regression tests pass**: all scenarios (with food, without food, market, no resources)
- **Determinism verified**: same seed produces identical results across runs
- **Before/after comparison**: agents no longer accumulate food indefinitely while starving
- **Test results**: `python -m pytest test_agent_eat.py -v` → 10 passed

### Files Changed
- agents/_agent.py: seek_food acquisition, eat redirect, planner restructuring
- docs/issues/Cycle2-correctness-no-food-critical-hunger.md: issue doc
- docs/decisions/001-eat-mechanic-no-food-critical-hunger.md: decision record
- test_agent_eat.py: 10 regression tests
- compare_before_after.py: before/after comparison script
- PROGRESS.md: this entry

### Category Rotation
Next cycle will focus on performance — checking for bottlenecks
in the simulation engine and optimizing where needed.

---

## Cycle 3: Emergent Depth — Multi-Agent World & Social System (Feb 2026)

### Observed Problem
The simulation had data structures for social dynamics (relationships,
social memory, organizations) but no mechanisms to make them emerge.
Agents could "socialize" but the action had no effect on relationships,
needs, or social memory. The world only had a single agent.

### Evidence
- 1 agent in world (agent-0 only)
- Relationship values never modified (always `{}`)
- Social memory tier always empty
- Organizations field always `None`
- Socialize action emitted `social_interaction` event but did nothing
- No conflict mechanism implemented
- No organization/joining mechanics

### Fix
1. **Multi-agent world**: `generate_world()` now creates 5 agents with
   randomized dispositions (friendly, neutral, hostile)
2. **Organization system**: Main Guild created with agent-0 as leader
3. **Socialize action**: Now modifies `relationships.values[target]`,
   creates `SocialMemory` entries, updates `needs.social`
4. **Social need in planner**: Added as priority (social < 0.3 triggers
   socialize, social < 0.6 triggers general socialize)
5. **Organization actions**: `form_organization` and `join_organization`
6. **Event handlers**: `social_interaction`, `fed`, `resource_gathered`,
   `organization_formed`, `joined_organization` in `SimulationCore`
7. **Social memory**: `add_social()` now called from socialize action

### Verification
- **13 regression tests pass**: multi-agent world, socialize mechanics,
  organization mechanics, determinism
- **23 total tests pass** (10 eat + 13 emergent depth)
- **Determinism verified**: same seed produces same agent configurations
- **Multi-agent world**: 5 agents, 1 organization, social dynamics active

### Files Changed
- simulation/world_gen.py: multi-agent world + organizations
- simulation/core.py: multi-agent processing, new event handlers
- simulation/_types.py: Organization dataclass
- agents/_agent.py: socialize action, organization actions, planner
- test_emergent_depth.py: 13 regression tests
- docs/issues/Cycle3-emergent-depth-social-system.md: issue doc
- PROGRESS.md: this entry
