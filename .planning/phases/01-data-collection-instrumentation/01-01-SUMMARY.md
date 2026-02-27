---
phase: 01-data-collection-instrumentation
plan: 01
title: "Pydantic Data Models for Decision Records and Agent Events"
one-liner: "DecisionRecord and AgentEvent Pydantic models with outcome tracking hooks, built-in validation, and factory methods for event creation"
subsystem: "Observability - Data Models"
tags: [data-models, pydantic, observability, phase-1]
status: complete
completed-date: 2026-02-27
execution-duration-minutes: 15
dependency-graph:
  requires:
    - id: "existing-agenttracker"
      description: "AgentTracker PredictionRecord pattern from backtracking module"
      via: "extends with outcome_pending and confidence fields"
  provides:
    - id: "decision-record-model"
      description: "DecisionRecord Pydantic model with outcome tracking hooks"
      used-by:
        - "plan-01-02: Instrumentation layer for capturing decisions"
        - "plan-01-03: Storage backend for persisting decisions"
    - id: "agent-event-model"
      description: "AgentEvent Pydantic model for execution event capture"
      used-by:
        - "plan-01-02: LangGraph event streaming integration"
        - "plan-01-03: Event storage and retrieval"
  affects:
    - "tradingagents/backtracking/agent_tracker.py: TradingSignal enum now exported from observability.models"
tech-stack:
  added:
    - library: "pydantic"
      version: "existing"
      purpose: "Data validation and BaseModel for type-safe models"
    - library: "datetime"
      version: "stdlib"
      purpose: "Timestamp generation and validation"
    - library: "uuid"
      version: "stdlib"
      purpose: "Unique ID generation for decisions and events"
  patterns:
    - "Pydantic BaseModel with Field() validators"
    - "Factory methods for object creation (create_llm_call, create_tool_use, etc.)"
    - "Type aliases for collections (DecisionRecords, AgentEvents)"
key-files:
  created:
    - path: "tradingagents/observability/models/decision_record.py"
      lines: 186
      purpose: "DecisionRecord Pydantic model with outcome tracking hooks"
    - path: "tradingagents/observability/models/agent_event.py"
      lines: 269
      purpose: "AgentEvent Pydantic model for execution event capture"
    - path: "tradingagents/observability/__init__.py"
      lines: 46
      purpose: "Observability module initialization with exports"
    - path: "tradingagents/observability/models/__init__.py"
      lines: 25
      purpose: "Models submodule exports and type aliases"
  modified:
    - path: "tradingagents/observability/models/__init__.py"
      changes: "Fixed imports, removed non-existent DebateState, added TradingSignal export and type aliases"
decisions:
  - id: "D01-01-01"
    title: "Use Pydantic BaseModel instead of dataclass"
    rationale: "Consistent with existing config models (TradingAgentsConfig), provides built-in validation, JSON serialization, and better IDE support"
    alternatives:
      - "dataclass: Simpler but no built-in validation"
      - "TypedDict: Less verbose but no runtime validation"
  - id: "D01-01-02"
    title: "Add outcome_pending field from day one"
    rationale: "Phase 5 (Performance Correlation) requires linking decisions to outcomes. Adding the field now prevents migration later"
    impact: "All DecisionRecord instances default to outcome_pending=True until outcome is calculated"
  - id: "D01-01-03"
    title: "Include confidence placeholder field"
    rationale: "Phase 2 (Confidence Scoring) will extract confidence scores. Field is optional (None) to avoid breaking existing code"
    impact: "Confidence can be added without schema changes"
  - id: "D01-01-04"
    title: "Use Literal type for event_type"
    rationale: "Provides type safety and IDE autocomplete for the four supported event types (llm_call, tool_use, state_transition, error)"
    alternatives:
      - "str: More flexible but loses type safety"
  - id: "D01-01-05"
    title: "Add factory methods to AgentEvent"
    rationale: "Simplifies event creation with pre-configured fields for each event type, reduces boilerplate"
    examples:
      - "AgentEvent.create_llm_call(agent_name, model, total_tokens=100)"
      - "AgentEvent.create_tool_use(agent_name, tool_name, tool_input={...})"
metrics:
  duration: "15 minutes"
  tasks-completed: "3/3"
  files-created: 4
  files-modified: 1
  loc-added: 526
  commits: 3
deviations-from-plan: []
---

# Phase 1 Plan 1: Pydantic Data Models Summary

## Overview

Created the foundational data models for the Trading Agents Observatory: **DecisionRecord** for capturing agent trading decisions with outcome tracking hooks, and **AgentEvent** for capturing granular execution events during LangGraph workflow execution. Both models use Pydantic BaseModels for type safety, validation, and JSON serialization.

**Key achievement:** Outcome tracking hooks (outcome_pending, entry_price, exit_price, hold_days) are built into the data model from day one (DATA-03 requirement), enabling Phase 5 (Performance Correlation) to link decisions to actual market outcomes without schema migrations.

## Created Models

### DecisionRecord (`tradingagents/observability/models/decision_record.py`)

**Purpose:** Capture agent trading decisions with built-in support for outcome correlation.

**Key features:**
- **Core context:** decision_id (UUID), ticker, trade_date, timestamp, run_id
- **Agent decision fields:** agent_name, agent_type (Literal with 7 types), decision, reasoning
- **Outcome tracking hooks (DATA-03):**
  - `outcome_pending: bool = True` - Tracks whether outcome calculation is pending
  - `entry_price: Optional[float]` - Price at trade entry
  - `exit_price: Optional[float]` - Price at exit
  - `hold_days: int = 7` - Days to hold for outcome calculation (matches existing AgentTracker pattern)
  - `return_pct: Optional[float]` - Calculated return percentage
  - `outcome_calculated: bool = False` - Whether outcome has been calculated
  - `outcome_calculated_at: Optional[datetime]` - Timestamp of outcome calculation
- **Confidence placeholder (Phase 2):** `confidence: Optional[float] = Field(None, ge=0.0, le=1.0)`
- **Debate/analysis capture:** bull_signal, bear_signal, risk_signal, final_signal (TradingSignal enums)
- **Metadata:** Dict[str, Any] for extensibility

**Validation:**
- `trade_date` must be in YYYY-MM-DD format
- `timestamp` must be valid ISO format
- `confidence` must be between 0.0 and 1.0 if provided

**Methods:**
- `to_dict()` - Serialize to dictionary (converts TradingSignal enums to values)
- `from_dict()` - Deserialize from dictionary (converts signal strings back to enums)
- `calculate_outcome(entry_price, exit_price)` - Calculate and update outcome metrics

### AgentEvent (`tradingagents/observability/models/agent_event.py`)

**Purpose:** Capture granular execution events during LangGraph workflow execution.

**Key features:**
- **Core fields:** event_id (UUID), event_type (Literal: "llm_call", "tool_use", "state_transition", "error"), agent_name, timestamp, run_id
- **Event-specific data:** data (Dict), metadata (Dict)
- **LLM call events:** model, prompt_tokens, completion_tokens, total_tokens
- **Tool use events:** tool_name, tool_input (Dict), tool_output (str)
- **State transition events:** from_state, to_state
- **Error events:** error_type, error_message

**Factory methods** (simplify event creation):
- `create_llm_call(agent_name, model, ...)`
- `create_tool_use(agent_name, tool_name, ...)`
- `create_state_transition(agent_name, from_state, to_state, ...)`
- `create_error(agent_name, error_type, error_message, ...)`

**Methods:**
- `to_dict()` - Serialize to dictionary (excludes None values for cleaner output)
- `from_dict()` - Deserialize from dictionary

## Module Structure

### `tradingagents/observability/__init__.py`

- Exports `DecisionRecord` and `AgentEvent` for easy import
- Module-level docstring with usage examples
- Version marker (`__version__ = "0.1.0"`) for future compatibility
- Logging configuration for the observability module

### `tradingagents/observability/models/__init__.py`

- Exports `DecisionRecord`, `AgentEvent`, `TradingSignal`
- Type aliases: `DecisionRecords = List[DecisionRecord]`, `AgentEvents = List[AgentEvent]`

## How Models Extend Existing AgentTracker Patterns

The existing `AgentTracker` module uses a `PredictionRecord` dataclass with outcome tracking:

```python
@dataclass
class PredictionRecord:
    ticker: str
    trade_date: str
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    hold_days: int = 7
    return_pct: Optional[float] = None
    outcome_calculated: bool = False
```

**DecisionRecord extends this pattern** by:
1. Converting from dataclass to Pydantic BaseModel (consistent with config models)
2. Adding agent context fields (agent_name, agent_type, decision, reasoning)
3. Adding `outcome_pending` flag to track which decisions need outcome calculation
4. Adding `outcome_calculated_at` timestamp for tracking when outcomes were computed
5. Adding confidence placeholder for Phase 2
6. Adding debate/analysis signal fields (bull_signal, bear_signal, risk_signal, final_signal)
7. Adding metadata dict for extensibility
8. Adding `run_id` for grouping events from a single graph execution

## Model Validation Rules

### DecisionRecord validators:
1. `trade_date` - Must be in YYYY-MM-DD format (raises ValueError if invalid)
2. `timestamp` - Must be valid ISO format string (raises ValueError if invalid)

### AgentEvent validators:
1. `timestamp` - Must be valid ISO format string (raises ValueError if invalid)
2. `event_type` - Constrained to Literal["llm_call", "tool_use", "state_transition", "error"]

## Default Values

**DecisionRecord defaults:**
- `outcome_pending: True` - All decisions start as pending outcome
- `hold_days: 7` - Matches existing AgentTracker pattern
- `outcome_calculated: False` - Outcomes not calculated by default
- `confidence: None` - Placeholder for Phase 2

**AgentEvent defaults:**
- Empty dicts for `data` and `metadata`
- None for all optional event-specific fields

## Requirements Satisfied

- **DATA-03:** Outcome tracking hooks built into data model from day one (outcome_pending, entry_price, exit_price, hold_days, return_pct, outcome_calculated, outcome_calculated_at)
- **DATA-04:** Structured data models for agent state transitions (AgentEvent with state_transition event type, from_state, to_state fields)

## Success Criteria Verified

- [x] DecisionRecord can be instantiated with ticker, trade_date, agent_name, agent_type, decision, reasoning
- [x] All outcome tracking fields default appropriately (outcome_pending=True, hold_days=7)
- [x] AgentEvent supports llm_call, tool_use, state_transition, and error event types
- [x] Both models serialize to JSON without errors
- [x] Models are accessible from tradingagents.observability namespace

## Deviations from Plan

None - plan executed exactly as written.

## Authentication Gates

None encountered.

## Next Steps

**Plan 01-02: Instrumentation Layer** - Use these models to capture decisions and events from LangGraph workflow execution via astream_events() and async queue pattern.

**Plan 01-03: Storage Backend** - Persist DecisionRecord and AgentEvent instances to SQLite with WAL mode for non-blocking writes.

**Plan 01-04: Integration** - Wire instrumentation into existing TradingAgentsGraph.propagate() to automatically capture all decisions.

## Self-Check: PASSED

**Created files:**
- ✓ tradingagents/observability/models/decision_record.py
- ✓ tradingagents/observability/models/agent_event.py
- ✓ tradingagents/observability/__init__.py
- ✓ tradingagents/observability/models/__init__.py

**Commits:**
- ✓ 61c5dca (DecisionRecord model with outcome tracking hooks)
- ✓ 6e3926e (AgentEvent model with full event type support)
- ✓ d13cb9d (Module structure and exports)
- ✓ 7ce25f3 (Summary and state updates)

**SUMMARY.md:**
- ✓ Created at .planning/phases/01-data-collection-instrumentation/01-01-SUMMARY.md
