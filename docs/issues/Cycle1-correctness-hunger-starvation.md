# Cycle 1: Correctness — Agents Cannot Eat (hunger always → 0)

## Observed Problem

In a deterministic 100-tick simulation (seed=42, 10×10 world), agents consistently
have their hunger need decay to 0 and remain there indefinitely. While agents can
`gather_food` (adding food to their inventory), there is no mechanism to convert
inventory food into hunger restoration.

### Evidence from tick 100 run

| Metric | Value |
|--------|-------|
| final_hunger | 0 |
| final_thirst | 0 |
| final_rest | ~0.5 |
| events of type `hunger_motivation` | 50 (one per tick once hunger < 0.5) |
| events of type `resource_gathered` (food) | varies by tick |
| agent inventory food amount | present but not consumed |

### Causal chain breakdown

1. Agent planner decides `seek_food` action (when hunger < 0.5)
2. `act("seek_food")` emits `hunger_motivation` event **but does not change agent state**
3. Need continues decaying at -0.01/tick
4. Hunger reaches 0 and stays there
5. No `eat` action exists to restore hunger from inventory `food` resources

### Impact

- Agents can never satisfy hunger through available actions
- The `gather_food` action is effectively a no-op for need satisfaction
- The economy's consume/produce system is disconnected from agent cognition
- Property-testable invariant broken: `same seed + gather_food ≠ hunger restoration`

## Proposed Approaches

### Approach A: Add `eat` action to agent `act()` method

**What:** Add an `elif action == "eat"` branch in `Agent.act()` that:
- Checks if inventory has food (`self.inventory.resources.get("food", 0) > 0`)
- Consumes 1 unit of food from inventory
- Restores hunger need: `self.needs.hunger = min(1.0, self.needs.hunger + 0.2)`
- Emits a `fed` event with data about food consumed

**Pros:**
- Minimal change (add one branch + one event type)
- Directly fixes the starvation issue
- Maintains determinism (food consumption is under agent control)
- Reuses existing inventory system
- Event-sourced: `fed` event adds to causal trace

**Cons:**
- Requires agent to deliberately choose `eat` action
- Does not automatically eat; agent must plan it

**Measurable criteria (before/after 100 ticks, seed=42):**
- `final_hunger` was: 0 → should be: >0 (e.g., 0.6 or higher when food in inventory)
- `events_of_type("fed")` should be: >0
- `events_of_type("hunger_motivation")` should still occur: ~50 (when hunger dips)

### Approach B: Automatically eat when food in inventory (passive)

**What:** Modify the `decide()` method so that if the agent has food in inventory
and hunger < 1.0, the planner automatically chooses `eat` without explicit
planning.

**Pros:**
- Agents eat automatically when they have food — more "realistic"
- No need for agent to explicitly plan eating

**Cons:**
- Less control over agent behavior
- Harder to distinguish intentional fasting vs. automatic eating
- Could mask other issues (e.g., agents never gathering food if they auto-eat)

**Measurable criteria:**
- Same as Approach A, but `eat` events would occur even without explicit planning

### Approach C: Increase hunger decay rate + add eat action

**What:** Combine Approach A with a modest increase to hunger decay rate
(e.g., -0.02/tick instead of -0.01/tick) so that agents feel a stronger
drive to eat, making the `eat` action more meaningful.

**Pros:**
- Creates stronger incentive for agents to seek/eat food
- More natural simulation of metabolic needs

**Cons:**
- Two changes in one cycle — harder to attribute results
- May cause faster starvation before eat action is planned

**Measurable criteria:**
- Hunger depletion speed increased by ~2x
- But `final_hunger` still >0 when food consumed

## Decision

**Selected: Approach A** — Add explicit `eat` action to `Agent.act()` method.

**Criteria:**
1. `final_hunger` must be >0 after 100 ticks when agent has food in inventory
   (criterion: final_hunger >= 0.5)
2. Determinism must be preserved: same seed + same actions = same final_hunger
3. Change must be minimal — add ≤50 lines of code, ≤1 new event type
4. Must not break save/load or replay functionality

**Rationale:** Approach A is the most targeted fix. It adds the missing link
between the economy (gather food) and agent cognition (eat food) without
automating agent behavior. It also introduces a new `fed` event that enriches
the causal trace for the "why did this happen?" observer feature planned for
later stages. Approach B (auto-eat) was rejected because it removes agent
agency, and Approach C (change decay rate) was rejected because it obscures
the root cause — the missing eat action.

## Implementation Next Steps

1. Add `elif action == "eat":` branch in `agents/_agent.py` `act()` method
2. Add `"fed"` event type to the event system
3. Add `eat` to the valid actions in `RuleBasedPlanner.plan()` (or as a
   default decision when hunger < 0.5 and food available)
4. Write regression test: 100-tick run with agent having food in inventory
   should result in final_hunger > 0
5. Verify replay reproducibility after the change