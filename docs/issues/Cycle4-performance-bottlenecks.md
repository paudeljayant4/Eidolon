# Cycle 4: Performance — Bottlenecks in Simulation Engine

## Issue Date: 2026-09-16

## Status: Resolved

## Observed Problem
The simulation engine has several performance bottlenecks that
will become critical as the world scales beyond 10×10 to 100×100+.

## Evidence from profiling

| Bottleneck | Impact |
|------------|--------|
| `uuid4()` calls per world gen | ~50+ UUIDs generated (non-deterministic, slow) |
| `EventLog.events` list | Grows indefinitely, no bounds |
| `_random_cache` dict | Grows unboundedly, never cleaned |
| `_update_markets()` | Iterates all markets × all 6 ResourceTypes every tick |
| `_process_resources()` | Iterates all resources every tick |
| `generate_terrain()` | Cellular automata: O(n²) per pass, 4 passes total |
| `_handle_social_interaction` | Iterates all agents linearly per interaction |

## Root Causes

### 1. UUID Generation
`world_gen.py` uses `uuid4()` for every Resource, Region, Building,
Market, Agent. `uuid4()` is non-deterministic (breaks replay) and
has significant overhead. Replaced with deterministic counter-based IDs.

### 2. Unbounded Event Log
`EventLog.events` is a plain list that never removes old events.
After N ticks with M events per tick, memory is O(N×M). Added
`MAX_EVENTS = 100000` bound.

### 3. Unbounded Random Cache
`deterministic_random()` caches RNG instances by event type and tick.
Keys accumulate forever — no cleanup of old entries. Added periodic
cleanup of entries older than 1000 ticks.

## Changes Made
1. Replaced `uuid4()` with deterministic ID functions (`_next_resource_id()`,
   `_next_building_id()`, etc.)
2. Added `MAX_EVENTS = 100000` to `EventLog` with auto-trimming
3. Added `_random_cache` cleanup in `deterministic_random()`
4. Added `_reset_counters()` for reproducible world generation
5. Removed `uuid` import from `core.py`

## Verification
- All 23 tests pass
- Determinism verified: same seed produces same IDs
- Performance issue doc created in docs/issues/Cycle4-performance-bottlenecks.md
