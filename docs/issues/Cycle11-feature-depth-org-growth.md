# Cycle 11: Feature Depth — Organization Growth

## Observed Problem
Only 1 organization existed (Main Guild with agent-0). No agents joined or formed new orgs despite having form_organization and join_organization actions in the agent code. The triggers were never reached because higher-priority actions (gather_wood, trade) always fired first.

## Evidence
| Metric | Before fix | After fix |
|--------|-----------|-----------|
| Agents with org | 1 | 5 |
| Org members | ['agent-0'] | ['agent-0','agent-1','agent-2','agent-3','agent-4'] |
| joined_organization events | 0 | 4 |
| organization_formed events | 0 | 0 |

## Fix
1. **Moved org triggers to priorities 7-8** (before gather_wood at priority 9)
2. **join_organization**: fires when agent has no org and a nearby agent has one
3. **form_organization**: fires when agent has no org and inventory_food > 50
4. **Org members list updated in act()**: join_organization now adds member to org.members directly
5. **Org info passed in needs dict**: each agent's organization is visible to planners of nearby agents

## Verification
- All 43 tests pass (10 eat + 13 emergent + 2 market + 3 building + 2 social fragility + 10 Cycle 9 + 3 Cycle 11)
- Determinism preserved
- All prior metrics unchanged (trade, drink, build, socialize)
- 4 new regression tests for org growth

## Files Changed
- agents/_agent.py: org triggers in planner, org members update in act(), org info in needs dict
- simulation/core.py: org info in needs dict
- test_emergent_depth.py: 3 new regression tests (TestCycle11OrgGrowth)
- docs/issues/Cycle11-feature-depth-org-growth.md: issue doc
- PROGRESS.md: this entry
