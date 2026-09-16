# Cycle 2: Correctness — No Food When Hunger is Critical

## Observed Problem

In the same deterministic 100-tick simulation (seed=42, 10×10 world) after the Cycle 1 fix,
agents now correctly eat when they have food in inventory. However, a new gap was exposed:
when hunger is critical (< 0.3) and the agent's inventory has **zero food**, the `eat` action
does not define any acquisition behavior. The agent emits a `hunger_motivation` event but
takes no action to acquire food — it simply continues to starve.

### Evidence from observation run

Running a 100-tick simulation with seed=42 where an agent starts with hunger=0.8 and zero food:

```
TICK 0: hunger=0.80, food_inv=0, action=seek_food → hunger_motivation event only
TICK 10: hunger=0.70, food_inv=0, action=seek_food → hunger_motivation event only
TICK 20: hunger=0.60, food_inv=0, action=seek_food → hunger_motivation event only
TICK 30: hunger=0.50, food_inv=0, action=seek_food → hunger_motivation event only
TICK 40: hunger=0.40, food_inv=0, action=seek_food → hunger_motivation event only
TICK 50: hunger=0.30, food_inv=0, action=seek_food → hunger_motivation event only
TICK 60: hunger=0.20, food_inv=0, action=seek_food → hunger_motivation event only
TICK 70: hunger=0.10, food_inv=0, action=seek_food → hunger_motivation event only
TICK 80: hunger=0.00, food_inv=0, action=seek_food → hunger_motivation event only
TICK 90: hunger=0.00, food_inv=0, action=seek_food → hunger_motivation event only
TICK 99: hunger=0.00, food_inv=0, action=seek_food → hunger_motivation event only
```

**Key metrics (before fix):**
- final_hunger: 0.0 (agent starves to death)
- events_of_type("fed"): 0
- events_of_type("hunger_motivation"): ~100 (one per tick)
- food acquired: 0 (seek_food does not actually acquire food)
- inventory_food at end: 0

The `seek_food` action in `Agent.act()` only emits a `hunger_motivation` event but never
actually acquires food from visible resources or the market. The agent is stuck in a
"seek but never acquire" loop.

### Causal chain breakdown

1. Agent planner sees hunger < 0.3, chooses `seek_food` action
2. `act("seek_food")` emits `hunger_motivation` event **but does not change agent state**
3. Need continues decaying at -0.01/tick
4. Hunger reaches 0 and stays there
5. No mechanism exists for the agent to acquire food when inventory is empty
6. The `seek_food` action is a no-op in terms of actual food acquisition

### The specific gap

The `eat` action branch in `Agent.act()` has this structure:

```python
elif action == "eat":
    food_amount = self.inventory.resources.get("food", 0)
    if food_amount > 0:
        # consume food, restore hunger
    else:
        # only emits hunger_motivation — no acquisition attempt
```

The `else` branch does not attempt to acquire food. It just emits a motivational event
and continues. This means agents with zero food and critical hunger will never recover.

## Proposed Approaches

### Approach A: Agent interrupts plan to acquire food (buy/produce)

**What:** When hunger is critical and inventory has zero food, the agent should interrupt
its current plan and actively acquire food — either gathering from visible resources or
buying from the market.

**Pros:**
- More realistic simulation behavior — starving agents seek food
- Agents can recover from critical hunger without external intervention
- Creates emergent narrative: "the agent went hungry but found food"
- Aligns with the agent cognitive architecture (perception → planning → action)
- Uses existing resource/market infrastructure

**Cons:**
- More complex implementation (need to handle resource gathering + market buying)
- May mask other issues if agents always find food easily
- Could create unintended feedback loops if gathering is too efficient

**Measurable criteria (before/after 100 ticks, seed=42, agent with zero food):**
- `final_hunger` should be > 0 (agent recovers from critical hunger)
- `events_of_type("resource_gathered")` with food should be: > 0 when resources available
- `events_of_type("fed")` should be: > 0 after acquisition
- `inventory_food` at end should be > 0 (agent acquired food)
- Agent should not crash

### Approach B: Agent takes hunger penalty and continues

**What:** When hunger is critical and inventory has zero food, the agent simply takes a
hunger penalty (e.g., additional -0.05 hunger) and continues its current behavior.

**Pros:**
- Simple implementation
- Clear mechanical consequence for being unable to eat
- Easy to tune and balance

**Cons:**
- Agents can never recover from critical hunger on their own
- Creates a "death spiral" where hunger always reaches 0
- Less realistic — real agents would seek food
- Less engaging from a narrative/simulation perspective

**Measurable criteria:**
- `final_hunger` would be 0 (or negative, clamped to 0)
- No food acquisition events
- `events_of_type("hunger_motivation")` would increase

### Approach C: Hybrid — acquire food if available, penalty if not

**What:** Combine Approach A and B — attempt to acquire food from visible resources/market,
but if none available, take a hunger penalty and continue.

**Pros:**
- Best of both worlds — realistic acquisition behavior + clear consequence when no food available
- More nuanced simulation
- Creates interesting trade-offs

**Cons:**
- Most complex to implement and tune
- Requires careful threshold design for when acquisition is attempted vs. penalty
- More edge cases to handle

**Measurable criteria:**
- `final_hunger` > 0 when food resources are visible
- `final_hunger` = 0 when no food resources are visible
- Hunger penalty events when no food available

## Decision

**Selected: Approach A** — The agent should interrupt its current plan to go acquire food.

**Rationale:** Approach A was selected because:
1. It creates a more realistic and engaging simulation where agents can recover from critical hunger
2. It leverages existing infrastructure (resource gathering, market system)
3. It creates emergent narrative possibilities
4. The `seek_food` action should be a meaningful action that actually acquires food, not just a motivational event
5. Approach B creates a death spiral where agents can never recover, breaking the simulation's usefulness
6. Approach C adds unnecessary complexity when the core behavior is clear: agents seek food when hungry

### Hunger thresholds chosen (currently arbitrary tuning constants — flag as such)

| Threshold | Value | Purpose | Notes |
|-----------|-------|---------|-------|
| `HUNGER_CRITICAL` | 0.3 | Triggers `seek_food` planning | Arbitrary tuning constant |
| `HUNGER_EAT_THRESHOLD` | 0.7 | Triggers `eat` planning when food available | Arbitrary tuning constant |
| `HUNGER_RESTORE_AMOUNT` | 0.2 | Hunger restored per food consumed | Arbitrary tuning constant |
| `HUNGER_DECAY_RATE` | 0.01 | Hunger decay per tick | Arbitrary tuning constant |
| `FOOD_GATHER_AMOUNT` | 10 | Food gained per gather action | Arbitrary tuning constant |
| `FOOD_GATHER_COST` | 1 | Food consumed per eat action | Arbitrary tuning constant |

These thresholds are **not derived from any analysis** — they are initial tuning constants
that should be validated through observation runs and adjusted as needed. They are flagged
here to prevent them from being buried as if they were scientifically determined.

## Implementation Plan

1. Modify `Agent.act("seek_food")` to actually acquire food from visible resources
2. Modify `Agent.act("eat")` `else` branch to redirect to food acquisition
3. Enhance `RuleBasedPlanner.plan()` to handle the no-food critical hunger case
4. Write regression tests for both scenarios
5. Verify determinism and before/after metrics
