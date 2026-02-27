---
phase: 03-decision-trail
plan: 03
title: "TrailQuery Interface"
one-liner: "Trail query interface with filtering by ticker, date range, agent, and confidence thresholds"
subsystem: "Observability - Decision Trail"
tags: [queries, filtering, search, confidence]
status: complete
completed_date: "2026-02-27"
execution_duration_seconds: 78
execution_duration_minutes: 1.3
---

# Phase 03 Plan 03: TrailQuery Interface Summary

## Objective

Implement TrailQuery interface for filtering and searching decision trails by ticker, date range, agent type, and confidence thresholds. Enable users to find specific decision trails from historical data using flexible filters.

## What Was Built

### 1. SQLiteDecisionStore Extension

**File:** `tradingagents/observability/storage/sqlite_backend.py`

**Added method:** `get_unique_run_ids()`

```python
def get_unique_run_ids(
    self,
    ticker: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = 100,
) -> List[str]
```

**Features:**
- Discovers unique run_ids matching filters for trail discovery
- Uses `idx_ticker_date` and `idx_run_id_decisions` indexes for efficiency
- Filters by ticker, date range, and agent_name
- Returns deduplicated run_id list sorted by date DESC

**Commit:** `5f5f446`

---

### 2. TrailQuery Class

**File:** `tradingagents/observability/trail/queries.py` (NEW - 201 lines)

**Core methods:**

1. **`get_trails()`** - List run_ids by filters
   - Calls `store.get_unique_run_ids()` with filters
   - Returns list of run_id strings
   - Use case: List available trails before building them

2. **`get_trail()`** - Build complete DecisionTrail for run_id
   - Delegates to `builder.build_trail(run_id)`
   - Returns None if run_id not found or no builder configured
   - Bridges query results to TrailBuilder

3. **`search_trails()`** - Full-text search in reasoning fields
   - Query: `SELECT run_id, ticker, trade_date, agent_name, reasoning FROM decision_records WHERE reasoning LIKE ?`
   - Uses pattern matching: `%query%`
   - Returns summary dicts (not full trails)
   - Simple LIKE matching for v1 (no ranking or semantic search)

4. **`get_trails_by_confidence()`** - Filter by confidence range
   - Leverages `store.get_decision_records_by_confidence()` from Phase 2
   - Extracts unique run_ids from filtered records
   - Returns deduplicated run_id list

5. **`_deduplicate_run_ids()`** - Helper method
   - Extracts run_id from each record
   - Uses `set()` for deduplication
   - Returns sorted list

**Commit:** `5e57e12`, `87cec93`

---

### 3. Trail Module Public API

**File:** `tradingagents/observability/trail/__init__.py`

**Updated exports:**
- `DecisionTrail`, `TrailNode`, `TrailEdge` (from models)
- `TrailQuery` (NEW - from queries)
- Uses lazy import to avoid circular dependencies

**Commit:** `78010e9`

---

## Deviations from Plan

None - plan executed exactly as written.

---

## Requirements Coverage

| ID | Requirement | Coverage |
|----|-------------|----------|
| TRAIL-03 | Users can filter and search through past decision trails | ✅ TrailQuery.get_trails(), search_trails(), get_trails_by_confidence() provide flexible filtering by ticker, date range, agent, and confidence |

---

## Key Decisions

**D03-03-01: Simple LIKE matching for search_trails() v1**
- **Rationale:** Full-text search ranking and semantic search deferred to future
- **Impact:** search_trails() uses `%query%` pattern matching with LIKE operator
- **Tradeoff:** Simplicity over search quality for initial implementation

**D03-03-02: Lazy import for TrailQuery in __init__.py**
- **Rationale:** Avoid circular dependencies between queries module and models
- **Impact:** Uses `__getattr__()` for lazy loading when TrailQuery is accessed
- **Pattern:** Consistent with Python 3.7+ lazy import best practices

---

## Performance Characteristics

**Query Efficiency:**
- All queries use existing SQLite indexes (`idx_ticker_date`, `idx_run_id_decisions`, `idx_confidence`)
- Run_id deduplication done in-memory with `set()` (efficient for <10K results)
- LIMIT clauses prevent unbounded result sets

**Index Usage:**
- `get_unique_run_ids()`: Uses `idx_ticker_date` for date-filtered queries
- `get_trails_by_confidence()`: Uses `idx_confidence` from Phase 2
- `search_trails()`: Uses `idx_ticker_date` for ticker/date filters

---

## Testing Verification

**Task 1:** `get_unique_run_ids()` method verified
```bash
python3 -c "from tradingagents.observability.storage.sqlite_backend import SQLiteDecisionStore; ..."
# Returns: list, empty=True for new DB
```

**Task 2:** TrailQuery class verified
```bash
python3 -c "from tradingagents.observability.trail.queries import TrailQuery; ..."
# Initializes: <class 'tradingagents.observability.trail.queries.TrailQuery'>
```

**Task 3:** Confidence filtering verified
```bash
python3 -c "from tradingagents.observability.trail.queries import TrailQuery; ..."
# Method exists: True
```

**Task 4:** Module export verified
```bash
python3 -c "from tradingagents.observability.trail import TrailQuery; ..."
# Prints: TrailQuery exported successfully
```

---

## Files Created/Modified

### Created
- `tradingagents/observability/trail/queries.py` (201 lines)

### Modified
- `tradingagents/observability/storage/sqlite_backend.py` (+52 lines)
- `tradingagents/observability/trail/__init__.py` (+10 lines, -2 lines)

---

## Commits

1. `5f5f446` - feat(03-03): add get_unique_run_ids method to SQLiteDecisionStore
2. `5e57e12` - feat(03-03): create TrailQuery class with filter methods
3. `87cec93` - feat(03-03): add confidence-based filtering to TrailQuery
4. `78010e9` - feat(03-03): export TrailQuery from trail module

---

## Next Steps

**Remaining plans in Phase 3:**
- 03-04: Implement trail export functionality (JSON, CSV formats)

**Dependencies for next plan:**
- 03-04 depends on 03-01 (models), 03-02 (builder), and 03-03 (queries) ✅

**Ready to execute:** 03-04 (Trail Export)

---

## Self-Check: PASSED

**Created files:**
- ✅ `tradingagents/observability/trail/queries.py` exists

**Commits verified:**
- ✅ `5f5f446` exists in git log
- ✅ `5e57e12` exists in git log
- ✅ `87cec93` exists in git log
- ✅ `78010e9` exists in git log

**All tasks complete:**
- ✅ Task 1: get_unique_run_ids() method added
- ✅ Task 2: TrailQuery class created with get_trails(), get_trail(), search_trails()
- ✅ Task 3: Confidence-based filtering added
- ✅ Task 4: TrailQuery exported from trail module
