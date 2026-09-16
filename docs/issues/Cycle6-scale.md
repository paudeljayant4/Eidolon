# Cycle 6: Scale Stress Test — Performance Bottleneck

## Observed Problem
Running the simulation at scale (50+ agents, 20x20+ worlds) revealed that `_update_markets()` iterates ALL markets × ALL resource types every tick, causing O(markets × resource_types) cost per tick. At 50x50 (2,500 markets), this is 15,000 iterations per tick, resulting in 4.8s for 100 ticks — too slow for meaningful large-scale observation.

## Evidence
- 5 agents, 10x10, 100 ticks: 3304 events, <0.1s
- 50 agents, 20x20, 200 ticks: 48013 events, 1.44s (before fix)
- 100 agents, 50x50, 100 ticks: 75045 events, 4.80s (before fix)
- Same seed produces identical results (determinism holds)
- No agent deaths at any scale

## Fix
1. Added `MARKET_UPDATE_INTERVAL = 10` class attribute to `SimulationCore`
2. `_update_markets()` now only runs every 10 ticks
3. Market events are batched into single `price_changed` events per market with `price_changes` dict
4. `_handle_price_changed` updated to handle both old and new formats for replay compatibility

## Before/After
| Scale | Before | After | Improvement |
|-------|--------|-------|-------------|
| 50 agents, 20x20, 200 ticks | 1.44s | 0.82s | 43% faster |
| 100 agents, 50x50, 100 ticks | 4.80s | 2.28s | 53% faster |

## Files Changed
- simulation/core.py: MARKET_UPDATE_INTERVAL throttling, batched market events, updated _handle_price_changed
- test_emergent_depth.py: test_market_update_throttled, test_market_events_batched
- docs/issues/Cycle6-scale.md: this issue doc
- PROGRESS.md: cycle entry
