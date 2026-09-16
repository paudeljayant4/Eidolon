# Cycle 3: Emergent Depth — Social System Is a No-Op

## Observed Problem

The simulation has the data structures for social dynamics (relationships,
social memory, organizations, conflict events), but none of the mechanisms
that would make them emerge are actually implemented. Agents can "socialize"
but the action has no effect on relationships, needs, or social memory.

### Evidence

**1. Single agent world — no multi-agent interaction possible**

`simulation/world_gen.py:generate_world()` creates only `agent-0`:
```python
agent = Agent(id="agent-0", ...)
```
There is no mechanism to spawn additional agents, so agents cannot form
relationships, conflicts, or guilds with each other.

**2. `socialize` action is a no-op**

`agents/_agent.py:407-411`:
```python
elif action == "socialize":
    events.append({
        "type": "social_interaction",
        "data": {"action": "socialize", "target": target or "unknown"}
    })
```
The action emits a `social_interaction` event but does NOT:
- Modify `self.relationships.values[target]`
- Modify `self.needs.social`
- Create `SocialMemory` entries via `self.memory.add_social()`
- Apply personality effects (disposition, altruism, riskTolerance)

**3. Social need is not tracked or decayed**

`Needs.social` exists in `_types.py:127` but `_decay_needs()` in
`simulation/core.py:184-205` does decay it (`-0.002/tick`), but:
- No planner checks `needs.social` to decide social actions
- No action satisfies the social need
- `needs.social` never influences agent behavior

**4. Relationship values never updated**

`Relationships.values` is a `Dict[str, float]` (agent_id → -1 to 1) but
no code ever modifies it. Relationships are initialized as empty `{}` and
remain empty forever.

**5. No organization/guild mechanism**

`Agent.organization` exists as `Optional[str]` but there is no code to
create, join, or manage organizations. The field is always `None`.

**6. No conflict mechanism**

`EventType.CONFLICT` exists in `_types.py:46` but there is no implementation
of conflict between agents. No `conflict` events are ever emitted.

**7. Social memory is never populated**

`AgentMemory.add_social()` exists but is never called from any action.
The `social` memory tier is always empty.

### Metrics from observation run

| Metric | Value |
|--------|-------|
| agents in world | 1 (agent-0 only) |
| relationship values modified | 0 |
| social memories created | 0 |
| organizations formed | 0 |
| conflict events emitted | 0 |
| social_interaction events | 0 (socialize never chosen by planner) |
| needs.social decayed | -0.002/tick (but never observed) |
| organize action exists | No |

### Causal chain breakdown

1. World generates with single agent and empty relationships
2. Planner never chooses `socialize` (no social need priority)
3. Even if `socialize` were chosen, the action does nothing
4. Relationship values remain `{}` forever
5. Social memory tier remains empty
6. No organizations or conflicts can form
7. The simulation has no emergent social dynamics

## Proposed Approaches

### Approach A: Implement multi-agent world + socialize mechanics

**What:** Spawn multiple agents, implement `socialize` to modify relationships
and create social memories, add social need to planner priorities, and
implement organization formation.

**Pros:** Creates genuine emergent social dynamics
**Cons:** Significant scope increase

### Approach B: Implement socialize mechanics + relationship tracking

**What:** Fix the `socialize` action to actually modify relationships and
create social memories. Add social need to planner. But keep single-agent
world.

**Pros:** More focused change, still demonstrates emergent behavior
**Cons:** Single agent can't form relationships with itself

### Approach C: Minimal fix — implement socialize + relationship tracking

**What:** Fix `socialize` to modify relationships when agents are nearby,
create social memories, decay social need properly. Keep existing world
structure.

**Pros:** Small change, meaningful improvement
**Cons:** Limited emergent depth without multiple agents

## Decision

**Selected: Approach A** — Implement multi-agent world + socialize mechanics.

**Rationale:** Emergent depth specifically requires multiple agents to
interact. A single agent cannot form relationships, conflicts, or guilds.
The full implementation creates the foundation for all emergent social
dynamics: multi-agent world, relationship tracking, social memory,
organization formation, and conflict mechanics.

## Next Steps

1. Spawn multiple agents in world generation
2. Implement `socialize` action to modify relationships and create social memories
3. Add social need to planner priorities
4. Implement organization/joining mechanics
5. Implement basic conflict mechanics
6. Add social memory creation to relevant actions
7. Write regression tests
8. Verify determinism and observer UI reflection
