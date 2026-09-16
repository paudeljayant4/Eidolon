# Decision Record: Eat Mechanic and No-Food Critical Hunger Behavior

## Date: 2026-09-16

## Status: Accepted

## Context

After the Cycle 1 fix that added the `eat` action to `Agent.act()`, a new gap was
identified: when hunger is critical (< 0.3) and the agent's inventory has zero
food, the `eat` action does not define any acquisition behavior. The agent emits
a `hunger_motivation` event but takes no action to acquire food — it simply
continues to starve indefinitely.

The core question was: does the agent interrupt its current plan to go acquire
food (buy/produce), or does it just take a hunger penalty and continue?

## Decision

**The agent should interrupt its current plan to go acquire food.**

When hunger is critical and inventory has zero food, the agent actively seeks to
acquire food from visible resources or the market. The `seek_food` action is
enhanced to actually gather food from available resources. The `eat` action's
`else` branch (when no food in inventory) redirects the agent to attempt food
acquisition.

## Eat Mechanic Details

### Normal eat behavior (food available)

- When `action == "eat"` and `inventory.resources["food"] > 0`:
  - Consumes 1 unit of food from inventory
  - Restores hunger: `needs.hunger = min(1.0, needs.hunger + 0.2)`
  - Emits `fed` event with data

### No-food critical hunger behavior (food NOT available)

- When `action == "eat"` and `inventory.resources.get("food", 0) == 0`:
  - The agent does NOT just emit a `hunger_motivation` event and stop
  - Instead, the agent redirects to `seek_food` to acquire food
  - `seek_food` checks visible resources for food
  - If food resources are visible and have amount > 0: gather food (+15 food to inventory)
  - If no visible food resources: emit `hunger_motivation` with reason "no food available"
  - Agent does NOT take a hunger penalty — it continues to seek food

### Planner behavior

- `RuleBasedPlanner.plan()` checks `inventory_food > 0 and hunger < 0.7` for `eat`
- When hunger < 0.3: planner chooses `seek_food` regardless of inventory state
- The `seek_food` action now actually acquires food from visible resources
- The `seek_food` action also checks the market for food availability

### Hunger thresholds (arbitrary tuning constants — flagged)

| Constant | Value | Purpose | Flag |
|----------|-------|---------|------|
| `HUNGER_CRITICAL` | 0.3 | Triggers `seek_food` planning | **ARBITRARY TUNING CONSTANT** |
| `HUNGER_EAT_THRESHOLD` | 0.7 | Triggers `eat` planning when food available | **ARBITRARY TUNING CONSTANT** |
| `HUNGER_RESTORE_AMOUNT` | 0.2 | Hunger restored per food consumed | **ARBITRARY TUNING CONSTANT** |
| `HUNGER_DECAY_RATE` | 0.01 | Hunger decay per tick | **ARBITRARY TUNING CONSTANT** |
| `FOOD_GATHER_AMOUNT` | 15 | Food gained per gather action | **ARBITRARY TUNING CONSTANT** |
| `FOOD_CONSUME_AMOUNT` | 1 | Food consumed per eat action | **ARBITRARY TUNING CONSTANT** |

These thresholds are **not derived from any analysis**. They are initial tuning
constants chosen for gameplay feel and should be validated through observation runs
and adjusted as needed. They are explicitly flagged as arbitrary here to prevent
them from being buried as if they were scientifically determined.

## Rationale

1. **Realism**: Agents that can seek food but never acquire it create an
   unrealistic "seek but never succeed" loop
2. **Emergent narrative**: Agents can recover from critical hunger, creating
   stories of survival
3. **Leverages existing infrastructure**: Resource gathering and market systems
   already exist; this just connects them to the `seek_food` action
4. **No penalty approach**: A hunger penalty would create a death spiral where
   agents can never recover, breaking the simulation's usefulness
5. **Minimal change**: The fix modifies existing action handlers rather than
   adding entirely new systems

## Verification Criteria

- Regression test: agent with food + elevated hunger, run N ticks → hunger decreases, inventory food decreases
- Regression test: agent with zero food + critical hunger, run N ticks → no crash, agent acquires food from visible resources
- Before/after comparison with 100 ticks, seed=42
- Determinism verified: same seed produces same results

## Related Issues

- Issue: docs/issues/Cycle2-correctness-no-food-critical-hunger.md
- Related to: docs/issues/Cycle1-correctness-hunger-starvation.md

## Related Code

- `agents/_agent.py`: `Agent.act()` method — `eat` and `seek_food` branches
- `agents/_agent.py`: `RuleBasedPlanner.plan()` — hunger thresholds and action selection
