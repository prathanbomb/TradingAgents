---
phase: 01-data-collection-instrumentation
plan: 02
subsystem: observability
tags: [langgraph, asyncio, pydantic, event-streaming, state-extraction]

# Dependency graph
requires:
  - phase: 01-data-collection-instrumentation
    plan: 01
    provides: [research findings, architecture patterns]
provides:
  - LanggraphCollector for non-blocking astream_events capture
  - StateExtractor for AgentState parsing into DecisionRecord objects
  - Pydantic models (AgentEvent, DecisionRecord, DebateState) for structured data
  - Integration helpers for easy adoption with existing TradingAgentsGraph
affects: [01-03-storage-pipeline, 03-decision-trail]

# Tech tracking
tech-stack:
  added: [langgraph.astream_events, asyncio, pydantic]
  patterns: [async event streaming, producer-consumer pattern, state extraction with signal parsing]

key-files:
  created:
    - tradingagents/observability/instrumentation/langgraph_collector.py
    - tradingagents/observability/instrumentation/state_extractor.py
    - tradingagents/observability/models/agent_event.py
    - tradingagents/observability/models/decision_record.py
  modified:
    - tradingagents/observability/__init__.py
    - tradingagents/observability/models/__init__.py
    - tradingagents/observability/instrumentation/__init__.py

key-decisions:
  - "Use LangGraph astream_events() for non-invasive event capture (no callbacks needed)"
  - "Filter events to avoid information overload (Pitfall #3 from research)"
  - "Reuse signal extraction pattern from agent_tracker.py for consistency"
  - "Add debate_state field to DecisionRecord for structured debate capture"

patterns-established:
  - "Pattern 1: Async event streaming via astream_events with event filtering"
  - "Pattern 2: State extraction with multiple extraction methods per agent type"
  - "Pattern 3: Convenience function (create_observation_run) for component creation"
  - "Pattern 4: Truncate long reports to 1000 chars to avoid storage bloat"

requirements-completed: [DATA-01, DATA-05]

# Metrics
duration: 3min
completed: 2026-02-27
---

# Phase 1 Plan 2: Non-blocking LangGraph Event Collection Summary

**Async LangGraph event streaming via astream_events and AgentState parsing with DecisionRecord extraction**

## Performance

- **Duration:** 3 min (236 seconds)
- **Started:** 2026-02-27T15:53:56Z
- **Completed:** 2026-02-27T15:56:52Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- **LanggraphCollector implementation** using LangGraph's astream_events() for non-blocking event capture
- **StateExtractor implementation** for parsing AgentState into DecisionRecord objects
- **Pydantic data models** (AgentEvent, DecisionRecord, DebateState) for structured observability data
- **Integration helpers** (create_observation_run) for easy adoption without breaking existing code
- **Signal extraction** reused from agent_tracker.py for consistency across codebase

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement LanggraphCollector for astream_events capture** - `3fb7b6b` (feat)
   - Created LanggraphCollector class with async event streaming
   - Implemented event filtering to capture only relevant events
   - Added token count extraction for LLM events
   - Added tool name/input/output extraction for tool events

2. **Task 2: Implement StateExtractor for AgentState parsing** - `a56d937` (feat)
   - Created StateExtractor class for parsing AgentState
   - Implemented extraction methods for all agent types
   - Reused signal extraction pattern from agent_tracker.py
   - Added debate_state field to DecisionRecord model

3. **Task 3: Create instrumentation module exports and integration helpers** - `e7346c9` (feat)
   - Added create_observation_run() convenience function
   - Exported LanggraphCollector and StateExtractor
   - Added get_instrumentation_config() for default configuration
   - Included integration pattern documentation

## Files Created/Modified

- `tradingagents/observability/instrumentation/langgraph_collector.py` - LangGraph event streaming collector
- `tradingagents/observability/instrumentation/state_extractor.py` - AgentState parser with signal extraction
- `tradingagents/observability/models/agent_event.py` - AgentEvent Pydantic model for execution events
- `tradingagents/observability/models/decision_record.py` - DecisionRecord and DebateState models
- `tradingagents/observability/__init__.py` - Module initialization with exports
- `tradingagents/observability/models/__init__.py` - Model exports (AgentEvent, DecisionRecord, DebateState)
- `tradingagents/observability/instrumentation/__init__.py` - Instrumentation exports and helpers

## Decisions Made

- **Use LangGraph astream_events() instead of callbacks** - Non-invasive, doesn't require modifying agent code
- **Filter events to avoid information overload** - Only capture LLM calls, tool usage, and chain transitions (Pitfall #3 from research)
- **Reuse signal extraction from agent_tracker.py** - Maintains consistency with existing prediction tracking
- **Add debate_state field to DecisionRecord** - Captures structured debate history for bull/bear researchers
- **Truncate long reports to 1000 chars** - Prevents storage bloat while preserving key reasoning

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added DebateState model and export**
- **Found during:** Task 2 (StateExtractor implementation)
- **Issue:** DecisionRecord model lacked debate_state field needed for researcher debate capture
- **Fix:** Added DebateState class to decision_record.py, updated __init__.py exports
- **Files modified:** tradingagents/observability/models/decision_record.py, tradingagents/observability/models/__init__.py
- **Verification:** StateExtractor successfully creates DecisionRecord with debate_state
- **Committed in:** a56d937 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Auto-fix necessary for capturing full decision context (DATA-05 requirement). No scope creep.

## Issues Encountered

- **Python import cache issues** - __pycache__ contained stale bytecode after adding DebateState export. Resolved by clearing cache before each test.
- **Model field validation** - Pydantic model validation failed when trying to set debate_state field that didn't exist. Fixed by adding field to DecisionRecord model.

## Verification Results

All tasks verified successfully:

1. **LanggraphCollector instantiation:**
   ```python
   collector = LanggraphCollector()
   assert collector.events == []
   # PASSED
   ```

2. **StateExtractor extraction:**
   ```python
   extractor = StateExtractor()
   records = extractor.extract_decision_records(test_state, 'AAPL', '2026-02-27')
   assert len(records) > 0
   # PASSED - Extracted 3 decision records (Market Analyst, Bull Researcher, Bear Researcher)
   ```

3. **Instrumentation exports:**
   ```python
   run_id, collector, extractor = create_observation_run('AAPL')
   assert collector.run_id == run_id
   # PASSED
   ```

## Integration Pattern

The instrumentation provides a non-invasive integration pattern with existing TradingAgentsGraph.propagate():

```python
from tradingagents.observability.instrumentation import create_observation_run

# Before propagate(): Create collector and extractor
run_id, collector, extractor = create_observation_run(ticker="AAPL")

# During propagate(): Stream events via collector.collect_events()
async for event in collector.collect_events(graph, input_state):
    # Events captured in real-time, non-blocking
    pass

# After propagate(): Extract decisions via extractor.extract_decision_records()
decision_records = extractor.extract_decision_records(final_state, ticker, trade_date, run_id)

# Pass both to async storage pipeline (Plan 03)
```

This pattern allows gradual adoption without modifying existing agent code.

## Next Phase Readiness

**Ready for Plan 03 (Async Storage Pipeline):**
- LanggraphCollector provides async event streaming
- StateExtractor provides DecisionRecord objects
- Data models (AgentEvent, DecisionRecord) are validated and ready
- Integration pattern established for non-blocking handoff to storage

**Blockers:** None

**Recommendations for Plan 03:**
- Use asyncio.Queue with producer-consumer pattern (from research Pattern 2)
- Implement batch writing to reduce I/O operations
- Consider SQLite with WAL mode for initial implementation
- Add retry logic for failed writes (tenacity library)

## Self-Check: PASSED

All created files verified:
- FOUND: langgraph_collector.py
- FOUND: state_extractor.py
- FOUND: agent_event.py
- FOUND: decision_record.py

All commits verified:
- FOUND: 3fb7b6b - LanggraphCollector
- FOUND: a56d937 - StateExtractor
- FOUND: e7346c9 - Integration helpers

---
*Phase: 01-data-collection-instrumentation*
*Plan: 02*
*Completed: 2026-02-27*
