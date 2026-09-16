# Cycle 8: Emergent Depth — Economy/Social Systems Disconnected from Agent Behavior

## Observation (500 ticks, seed=42, 20x20 world, 5 agents)

| Metric | Value |
|--------|-------|
| Total trade events | **0** |
| Total socialize events | **0** |
| Total build events | **0** |
| Building production events | 156 (farms producing food) |
| Unique trade pairs | 0 |
| Unique social pairs | 0 |
| Final orgs | 1 (Main Guild, 1 member) |
| Food (start → end) | 36,620 → 57,717 (+58%) |
| Water (start → end) | 0 → 0 (farms consume, no production) |
| Agent hunger (avg) | 0.99 → 0.00 (starvation) |
| Agent health (avg) | 1.00 → 0.00 (death) |
| Agent energy (avg) | 1.00 → 0.00 |
| Agent social (avg) | 1.00 → 0.00 |

### Key Findings
1. **Zero trade events** — `trade` action exists (Cycle 5) but never fires
2. **Zero socialize events** — `socialize` exists (Cycle 3) but never fires
3. **Zero build events** — `build` exists (Cycle 7) but never fires
4. **Agents starve amid plenty** — Food surges 36K→57K, but agent hunger crashes to 0
5. **Water crisis** — Farms consume water; water resources at 0 with no production
6. **No org growth** — Only initial Main Guild (1 member), no new orgs formed
7. **Agents die** — Health reaches 0 by tick ~300

## Diagnosis

Two interconnected gaps prevent any emergent economy/social behavior:

### Gap A: Simulation loop doesn't execute agent decisions
`SimulationCore.tick_step()` calls `_process_agents()` which only emits `hunger_motivation`/`thirst_motivation`/`social_motivation` events. It **never calls** `agent.perceive()`, `agent.decide()`, or `agent.act()`. The tests pass because they manually call `agent.decide()` and `agent.act()` — the actual simulation loop doesn't.

### Gap B: Planner lacks trade/build/socialize logic
`RuleBasedPlanner.plan()` has decision logic for: `eat`, `seek_food`, `seek_water`, `rest`, `socialize` (only if `nearby_agents`), `gather_wood`, `gather_iron`, `gather_food`, `explore`. It has **no logic for `trade`, `build`, or proactive socialize**. `trade` and `build` were added to valid actions (Cycle 5/7) but never to the decision tree. `socialize` is gated on `perception.nearby_agents` which is **never populated** (agent.perceive() doesn't fill it).

### Gap C: Water economy broken
Farms consume water each tick but no building produces water. Water resources stay at 0 → farms can't sustain production → long-term food production fails.

## Root Cause
The economy (farms, markets, trade), social system (relationships, orgs, socialize), and politics (org formation) exist as **disconnected subsystems**. Agents don't act in the simulation loop, and even if they did, the planner doesn't know how to use trade/build/socialize to respond to resource signals.

## Candidate Approaches

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A1: Fix sim loop + add planner logic** | Modify `tick_step` to call `agent.perceive/decide/act` for each agent; add `trade`/`build`/`socialize` conditions to `RuleBasedPlanner`; populate `nearby_agents` in perception | Enables all existing actions; completes the architecture | Larger change; touches core loop + planner |
| **A2: Fix sim loop only** | Just add agent decision loop to `tick_step`; leave planner as-is (agents will only eat/seek/gather/explore) | Smaller change; validates loop works | Trade/build/socialize still unused; no economic/social coupling |
| **A3: Fix planner only** | Add `trade`/`build`/`socialize` to planner; leave sim loop broken | Tests would pass (they call decide/act manually) | Simulation still produces no emergent behavior |
| **A4: Add water production** | Add water-producing building (well/pump) or water resource regrowth | Fixes water crisis | Doesn't address agent behavior gap |
| **A5: Scale up world first** | Run larger/longer observation before fixing | Might reveal behavior at scale | Current behavior is fundamentally broken; scale won't fix 0 actions |

## Recommendation
**Approach A1** — The simulation loop fix is necessary for any agent behavior at all. The planner fix is necessary for economic/social coupling. These are two halves of the same architecture completion. Doing one without the other leaves the system broken. This is not "busywork" — it completes the architecture that Cycles 3, 5, 7 partially built.

Water fix (A4) should be included as part of A1 since it's a resource dependency.