# Cycle 5: Feature Depth — Missing Features

## Issue Date: 2026-09-16

## Status: In Progress

## Observed Problem
The simulation has defined event types, actions, and data structures
that are referenced in the planner and LLM prompt, but many are
not implemented in `Agent.act()` or `SimulationCore._apply_event()`.

## Missing Features Identified

### 1. `trade` action referenced but not implemented
- `Agent.act()` has no `elif action == "trade"` branch
- LLM prompt includes "trade" as a valid action
- Market prices exist but no mechanism to buy/sell

### 2. Missing event handlers in `SimulationCore._apply_event()`
- `EventType.BIRTH`, `DEATH`, `CONFLICT`, `BUILD`, `RESEARCH`
- `EventType.RESOURCE_DEPLETION`, `ELECTION`, `TREATY`, `WAR`
- `EventType.MINE_COLLAPSE`, `FLOOD`, `FAMINE`
- Only `resource_growth`, `price_changed`, `hunger_motivation`,
  `thirst_motivation`, `moved`, `traded`, `rested`, `need_decay`
  `social_interaction`, `fed`, `resource_gathered`, `organization_formed`,
  `joined_organization` are handled

### 3. `health` and `energy` not modified by any action
- `Agent.health` and `Agent.energy` fields exist but are never changed
- No action affects them

### 4. `safety` need not implemented
- `Needs.safety` exists but no action affects it
- No planner checks `needs.safety`

### 5. `skill` development not implemented
- `Skills.values` exists but doesn't change through use
- No training/learning mechanism

### 6. `build` action not implemented
- Buildings exist in regions but agents can't build them
- `BuildingType` includes BUILDING types but no build action

## Proposed Implementation

### Phase 1: Trade action + market interaction
- Implement `trade` action to buy/sell food from market
- Agent needs `inventory_food` and `market_prices` to trade

### Phase 2: Missing event handlers
- Add `_handle_conflict`, `_handle_death`, `_handle_build`
- Add `_handle_trade` to update agent inventories

### Phase 3: Health/energy/safety mechanics
- Modify `health` and `energy` based on actions
- Add `safety` to planner priorities

## Decision

**Selected: Phase 1 (Trade action) + Phase 2 (Event handlers) + Phase 3 (Health/energy)**

**Rationale:** Trade is the most impactful missing feature — it
connects the market system to agent behavior. Event handlers complete
the simulation. Health/energy/safety add depth to agent mechanics.

## Next Steps
1. Implement `trade` action in `Agent.act()`
2. Add missing event handlers in `SimulationCore._apply_event()`
3. Add health/energy/safety mechanics
4. Write regression tests
5. Verify determinism
