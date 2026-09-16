# Decision: Cycle 8 — Fix Agent Decision Loop + Planner Logic

## Context
Cycle 8 observation revealed agents never act in the simulation loop (0 trade, 0 socialize, 0 build events over 500 ticks), causing starvation amid massive food surplus and complete absence of economic/social behavior.

## Decision
**Implement Approach A1: Fix simulation loop + planner logic + water production**

## Rationale
- The simulation loop fix is a prerequisite for ANY agent behavior
- The planner fix is required for economic/social coupling (trade/build/socialize)
- Water production fixes the resource dependency chain (farms need water)
- These are interdependent — doing one without the other leaves the system fundamentally broken

## Acceptance Criteria
1. **Simulation loop executes agent decisions**: Each tick, every agent calls `perceive()` → `decide()` → `act()`
2. **Planner supports trade/build/socialize**: `RuleBasedPlanner.plan()` includes conditions for all three actions
3. **Perception includes nearby agents**: `agent.perceive()` populates `nearby_agents` within configurable radius
4. **Water production exists**: Add water-producing building (Well) or resource regrowth
5. **Before/after metrics**: 
   - Trade events > 0 per 100 ticks
   - Socialize events > 0 per 100 ticks  
   - Build events > 0 per 100 ticks
   - Agent hunger avg > 0.3 at tick 500 (no mass starvation)
   - Water resources > 0 at tick 500
   - Determinism preserved (same seed → same results)

## Implementation Plan
1. **SimulationCore.tick_step**: Add agent decision loop after `_process_agents`
2. **RuleBasedPlanner.plan**: Add `trade` (when inventory surplus + market visible), `build` (when resources + need), `socialize` (lower threshold, no nearby_agents requirement initially)
3. **Agent.perceive**: Add `nearby_agents` detection within radius
4. **World gen**: Add Well building type that produces water
5. **Tests**: Add regression tests for each new behavior

## Risks
- Larger change than typical cycle — but it's completing the architecture, not adding new features
- Determinism must be verified — same seed must produce identical results
- Performance: 5 agents × 500 ticks is trivial; 100 agents × 500 ticks should still be <5s

## Decision Maker
Cycle 8 lead (this session)

## Date
2026-09-16