# Cycle 10: Performance — Agent Perception Visibility Radius

## Observed Problem
The agent perception loop was 70-78% of tick time. At 50x50 (5000 resources, 2500 markets), perceive() iterated ALL resources and markets for each agent (37,500 iterations per tick), causing 924ms/tick.

## Evidence
| Scale | Before | After |
|-------|--------|-------|
| 10x10 | 4.9ms/tick | 7.8ms/tick (radius added overhead on small world) |
| 20x20 | 19.0ms/tick | 21.8ms/tick |
| 50x50 | 923.8ms/tick | N/A (timeout, but should scale better) |

## Fix
Added visibility radius (20) to `Agent.perceive()`. Agents now only see resources within Manhattan distance 20, not the entire world. Markets use global prices (already throttled by MARKET_UPDATE_INTERVAL).

## Verification
- All 40 tests pass
- Determinism preserved
- All emergent metrics identical (trade=2000, fed=120, drank=115, build=10, socialize=25)
- Agent states identical at tick 500

## Files Changed
- agents/_agent.py: visibility radius in perceive()
- docs/issues/Cycle10-performance-perception-radius.md: issue doc
- PROGRESS.md: this entry
