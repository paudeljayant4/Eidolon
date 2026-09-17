# Cycle 9: Emergent Depth — Water/Rest/Trade Integration Fixes

## Observed Problem
After Cycle 8 connected agents to the tick loop, 500-tick observation revealed:
1. **Thirst stuck at 0**: All agents have 5,775 water in inventory but drink action never fires. `seek_water` (priority 5) fires when thirst < 0.3, blocking `drink` (priority 6). Agents gather water but never consume it.
2. **Energy oscillation**: Energy hits 0 at tick 100, oscillates 0-0.24 for 400 ticks. Rest condition requires `rest < 0.3 AND energy < 0.5`, but rest decays slowly (0.005/tick), delaying recovery by ~140 ticks.
3. **Trade dies after tick 100**: All 325 trades in first 100 ticks (all sell_food), then hunger > 0.8 stops trade. No buy events occur.
4. **Zero build events**: No agent gathers wood (gather_wood at priority 6, never reached).
5. **Partner diversity = 0**: Planner always picks `nearby_agents[0]`, only agent-0 and agent-1 socialize.
6. **Organization stuck**: Only 1 org (Main Guild with agent-0). No growth mechanism triggered.

## Evidence
| Metric | Value |
|--------|-------|
| Drink events | 0 |
| Thirst at tick 500 | 0.000 (all agents) |
| Water in inventory | 5,775 per agent |
| Trade events after tick 100 | 0 |
| Build events total | 0 |
| Socialize partners | agent-0 and agent-1 only |
| Organizations | 1 (no growth) |

## Proposed Fixes

### Fix 1: Swap drink/seek_water priorities
**Before**: seek_water (priority 5) → drink (priority 6)
**After**: drink (if inventory_water > 0) → seek_water (only if no water)

This matches the eat/seek_food pattern already established.

### Fix 2: Relax rest condition
**Before**: `rest < 0.3 AND energy < 0.5`
**After**: `energy < 0.4` (rest when energy is low, regardless of rest value)

Energy decay (0.005/tick) is fast enough that resting is always appropriate when energy is low.

### Fix 3: Random partner selection
**Before**: `perception.nearby_agents[0]`
**After**: `random.choice(perception.nearby_agents)`

Ensures diverse social interactions.

### Fix 4: Lower wood gathering threshold
**Before**: `visible_resources.get("wood", 0) > 30`
**After**: `visible_resources.get("wood", 0) > 10`

Makes wood gathering reachable in the decision chain.

### Fix 5: Sustain trade via sell-surge mechanism
Add periodic sell when inventory_food > 10 (not just > 5) to maintain economic activity.

## Decision Criteria
- Thirst must be non-zero at tick 500 (agents drink)
- Energy must not be stuck at 0 for >100 consecutive ticks
- Trade events must occur after tick 100
- Socialize must involve at least 3 different agents
- All 30 existing tests must pass
- Determinism preserved
