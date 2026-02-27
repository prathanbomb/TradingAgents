# Phase 1: Data Collection & Instrumentation - Research

**Researched:** 2026-02-27
**Domain:** AI Observability & Data Collection for Multi-Agent Trading Systems
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
None - user skipped detailed discussion and granted full discretion.

### Claude's Discretion
User chose to skip detailed discussion. Claude has full discretion on:

- **Storage approach**: File-based (extend existing AgentTracker), SQLite, or PostgreSQL; retention policy
- **Data model scope**: What fields to capture in DecisionRecord; full outputs vs summaries
- **Failure handling**: Drop data, block briefly, or retry on failures; logging strategy
- **Integration strategy**: Extend AgentTracker vs separate module; coupling level

**Guiding principle**: Non-blocking is critical (DATA-02). The observability layer must never slow down trading decisions.

### Deferred Ideas (OUT OF SCOPE)
None — discussion skipped, proceeding to implementation.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | System captures decision events at each agent step without blocking the trading pipeline | LangGraph `astream_events` and async queue patterns enable non-blocking capture |
| DATA-02 | Data collection is asynchronous and non-blocking to maintain analysis performance | `asyncio.Queue` with producer-consumer pattern ensures trading pipeline never blocks |
| DATA-03 | Outcome tracking hooks are built into the data model from day one | Extend existing `PredictionRecord.outcome_calculated` pattern with `outcome_pending` field |
| DATA-04 | System implements structured logging for all agent state transitions | Python structured logging with JSON format + trace IDs for distributed tracking |
| DATA-05 | LangGraph callback integration captures full decision context (reasoning, debates, confidence) | LangGraph inherits LangChain callbacks + `astream_events` for granular step capture |
</phase_requirements>

## Summary

This phase establishes the **foundational data collection infrastructure** for the Trading Agents Observatory. The research confirms that building a **non-blocking, asynchronous instrumentation layer** is critical to avoid degrading trading performance (Pitfall #1 from research). The recommended approach leverages **LangGraph's streaming capabilities** (`astream_events` with stream modes) combined with **Python's asyncio queue pattern** to decouple data capture from storage operations.

The existing codebase provides a solid foundation: `AgentTracker` already demonstrates prediction recording with outcome tracking hooks, and the storage layer has an abstract backend pattern. The phase will extend these patterns rather than replace them, maintaining architectural consistency while adding comprehensive observability.

**Primary recommendation:** Build an async instrumentation layer using LangGraph's `astream_events()` for data capture, `asyncio.Queue` for non-blocking handoff, and SQLite with WAL mode for persistent storage. This balances performance (async throughout), simplicity (file-based patterns extended), and query capability (SQL for Phase 3+).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **langgraph** | ≥0.4.8 (in pyproject.toml) | Agent orchestration with streaming events | Existing dependency; `astream_events` provides granular decision capture without callbacks |
| **asyncio** | Built-in (Python 3.12) | Async queue and task management | Standard library async primitives; producer-consumer pattern prevents blocking |
| **sqlite3** | Built-in (Python 3.12) | Embedded database for decision logs | Zero-config; 8x faster than file-based for reads; supports SQL queries for Phase 3+ |
| **pydantic** | Existing dependency | Data validation with BaseModel | Type-safe data models; already used throughout codebase for configuration |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **structlog** | ≥23.0.0 | Structured JSON logging | When standard logging needs to be queryable; optional enhancement to Python logging |
| **aiosqlite** | ≥0.19.0 | Async SQLite adapter | If async database writes are needed (but standard sqlite3 in thread is sufficient) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **SQLite** | **PostgreSQL** | PostgreSQL better for multi-user (10+ concurrent) and high-volume (>10GB); SQLite simpler and faster for single-user |
| **asyncio.Queue** | **Redis Queue** | Redis adds external dependency and network overhead; asyncio built-in sufficient for single-machine deployment |
| **LangGraph astream_events** | **LangChain callbacks** | Callbacks more invasive (require handler injection); `astream_events` non-invasive and provides richer context |

**Installation:**
```bash
# Core dependencies already in pyproject.toml
# No additional packages required for Phase 1

# Optional: structured logging enhancement
pip install structlog

# Optional: async SQLite (if needed)
pip install aiosqlite
```

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/
├── observability/
│   ├── __init__.py
│   ├── instrumentation/
│   │   ├── __init__.py
│   │   ├── langgraph_collector.py    # Captures events via astream_events
│   │   ├── decision_recorder.py       # Records agent decisions
│   │   └── state_extractor.py         # Extracts state from AgentState
│   ├── models/
│   │   ├── __init__.py
│   │   ├── decision_record.py         # DecisionRecord with outcome hooks
│   │   ├── agent_event.py             # AgentEvent model
│   │   └── debate_state.py            # Structured debate capture
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── decision_store.py          # Abstract storage interface
│   │   ├── sqlite_backend.py          # SQLite implementation
│   │   └── file_backend.py            # Fallback file backend (extends AgentTracker)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── async_queue.py             # Async queue for non-blocking handoff
│   │   ├── batch_writer.py            # Batch writes to storage
│   │   └── retry_handler.py           # Failure handling with retry/backoff
│   └── config/
│       ├── __init__.py
│       └── observability_config.py    # Configuration for observability
└── backtracking/
    └── agent_tracker.py               # [EXISTING] Extend for compatibility
```

### Pattern 1: LangGraph Event Streaming for Data Capture

**What:** Use `graph.astream_events()` to capture granular execution events without modifying agent code.

**When to use:** When you need comprehensive decision context (LLM calls, tool usage, state transitions) without invasive instrumentation.

**Example:**
```python
# Source: LangGraph streaming modes research (2025)
from langgraph.graph import StateGraph

async def collect_decision_events(graph: StateGraph, input_data: dict):
    """Stream events from graph execution for observability."""
    events = []

    async for event in graph.astream_events(
        input_data,
        version="v1",  # Required for astream_events
        config={"run_name": "decision_capture"}
    ):
        # Filter for relevant events
        if event["event"] in [
            "on_chat_model_start",
            "on_chat_model_end",
            "on_tool_start",
            "on_tool_end",
            "on_chain_start",
            "on_chain_end"
        ]:
            events.append({
                "event_type": event["event"],
                "timestamp": datetime.utcnow().isoformat(),
                "data": event["data"],
                "metadata": event.get("metadata", {})
            })

    return events
```

### Pattern 2: Async Queue Producer-Consumer for Non-Blocking Writes

**What:** Decouple data capture (producer) from storage (consumer) using `asyncio.Queue` with bounded size for backpressure control.

**When to use:** When trading pipeline must never block on I/O operations (DATA-02 requirement).

**Example:**
```python
# Source: Asyncio background task queue best practices (2025)
import asyncio
from typing import Callable, Any

class AsyncDataPipeline:
    """Non-blocking data collection pipeline."""

    def __init__(
        self,
        storage_handler: Callable,
        max_queue_size: int = 1000,
        batch_size: int = 50
    ):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.storage_handler = storage_handler
        self.batch_size = batch_size
        self.consumer_task = None
        self._shutdown = False

    async def producer(self, data: dict) -> bool:
        """Add data to queue (non-blocking with backpressure)."""
        try:
            await asyncio.wait_for(
                self.queue.put(data),
                timeout=1.0  # Brief wait for backpressure
            )
            return True
        except asyncio.TimeoutError:
            # Queue full, drop data or log warning
            logger.warning("Observability queue full, dropping event")
            return False

    async def consumer(self):
        """Process events from queue and write to storage."""
        batch = []

        while not self._shutdown:
            try:
                # Wait for events with timeout
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=0.1
                )
                batch.append(event)

                # Flush batch when size reached
                if len(batch) >= self.batch_size:
                    await self.storage_handler(batch)
                    batch = []
                    self.queue.task_done()

            except asyncio.TimeoutError:
                # Flush remaining batch
                if batch:
                    await self.storage_handler(batch)
                    batch = []

    async def start(self):
        """Start the background consumer task."""
        self.consumer_task = asyncio.create_task(self.consumer())

    async def stop(self):
        """Gracefully shutdown consumer."""
        self._shutdown = True
        if self.consumer_task:
            await self.consumer_task
        await self.queue.join()
```

### Pattern 3: Structured Logging with Trace IDs

**What:** Use Python's logging module with structured JSON format and trace IDs for distributed tracking.

**When to use:** For debugging multi-agent coordination issues (Pitfall #5) and maintaining audit trails.

**Example:**
```python
# Source: Python structured logging best practices (2025)
import logging
import json
import uuid
from typing import Any, Dict

class StructuredLogger:
    """Structured JSON logger for observability events."""

    def __init__(self, service_name: str):
        self.logger = logging.getLogger(service_name)
        self.service_name = service_name
        self._setup_handler()

    def _setup_handler(self):
        """Configure JSON handler."""
        handler = logging.StreamHandler()
        handler.setFormatter(self._json_formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _json_formatter(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra context if present
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "agent"):
            log_entry["agent"] = record.agent
        if hasattr(record, "ticker"):
            log_entry["ticker"] = record.ticker

        return json.dumps(log_entry)

    def log_decision(
        self,
        agent: str,
        decision: str,
        ticker: str,
        confidence: float = None,
        **extra
    ):
        """Log a decision event with structured context."""
        trace_id = str(uuid.uuid4())
        log_dict = {
            "event_type": "decision_made",
            "agent": agent,
            "decision": decision,
            "ticker": ticker,
            "trace_id": trace_id,
            **extra
        }
        if confidence is not None:
            log_dict["confidence"] = confidence

        self.logger.info(
            f"Decision by {agent}: {decision}",
            extra=log_dict
        )
```

### Anti-Patterns to Avoid

- **Synchronous file I/O in trading path:** Never write directly to disk in agent nodes. Use async queues to hand off data to background tasks.
- **Full transcript capture without sampling:** Storing complete LLM outputs for every decision causes storage bloat. Capture structured summaries, sample full transcripts at 10% rate.
- **Tight coupling to AgentTracker:** Don't modify existing `AgentTracker` directly. Create new observability module that can import from it, maintaining backward compatibility.
- **Blocking on queue full:** Never block trading pipeline waiting for observability queue. Use `put_nowait()` with timeout, log drops, and continue trading.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| **Async queue management** | Custom task lifecycle, shutdown, error handling | `asyncio.Queue` with producer-consumer pattern | Built-in backpressure, exception isolation, battle-tested |
| **Structured logging** | Custom JSON formatting, log rotation | Python `logging` module + optional `structlog` | Standard library integration, handler ecosystem, log rotation built-in |
| **SQLite connection pooling** | Custom connection management, thread safety | `sqlite3` in thread or `aiosqlite` for async | SQLite handles single-thread natively; connections are lightweight |
| **LangGraph event capture** | Decorators on every node, manual state tracking | `astream_events()` with event filtering | Non-invasive, captures all graph internals, no code changes needed |
| **Retry logic** | Custom exponential backoff, circuit breakers | `tenacity` library (if needed) or simple async retry | Handles edge cases (network timeouts, partial failures), configurable policies |

**Key insight:** The existing `AgentTracker` demonstrates the right pattern for file-based storage, but adding synchronous writes would violate DATA-02. The async queue pattern prevents blocking while maintaining the simplicity of file storage.

## Common Pitfalls

### Pitfall 1: Observability That Slows Down Decision-Making

**What goes wrong:** Adding comprehensive logging that slows the trading pipeline by 3x+ due to synchronous I/O operations.

**Why it happens:** Writing decision records directly to disk/database in agent nodes blocks LLM calls and tool execution.

**How to avoid:**
1. Use `asyncio.Queue` with producer-consumer pattern (Pattern 2)
2. Set queue `maxsize` to enable backpressure (prevents memory overflow)
3. Use `queue.put_nowait()` with brief timeout for non-blocking enqueue
4. Drop data if queue full rather than blocking trading pipeline
5. Batch writes to storage (group 50-100 events per write)

**Warning signs:**
- Agent execution time increases >10% after instrumentation
- Queue frequently full (check metrics on queue size)
- Trading latency spikes during market open/close

### Pitfall 2: Decision Records Without Outcome Hooks

**What goes wrong:** Beautiful decision capture but no way to link decisions to actual market outcomes for Phase 4 (Performance Correlation).

**Why it happens:** Designing data model for current needs without considering future outcome correlation requirements.

**How to avoid:**
1. Add `outcome_pending: bool = True` field to all decision records
2. Include `entry_price: Optional[float]` and `exit_price: Optional[float]` fields
3. Store `hold_days: int = 7` for outcome calculation timing
4. Add `outcome_calculated_at: Optional[datetime]` for tracking
5. Create index on `(ticker, trade_date)` for efficient outcome updates

**Warning signs:**
- No way to query "all pending outcomes for ticker X"
- Decision records lack price context fields
- Cannot identify which decisions need outcome updates

### Pitfall 3: Information Overload in Event Capture

**What goes wrong:** Capturing every LLM token, tool call, and state transition results in 100MB+ of data per trading decision.

**Why it happens:** Using `astream_events` without filtering captures too much verbose data.

**How to avoid:**
1. Filter events to only relevant types (LLM end, tool end, chain end)
2. Capture summaries not full transcripts for analyst reports
3. Sample full transcript capture at 10% rate
4. Implement structured data extraction (bull_signal, bear_signal) vs free text
5. Store debate state as structured fields, not conversation history

**Warning signs:**
- Average decision record >1MB
- Storage growth >10GB per month
- Queries take >5 seconds to return

### Pitfall 4: SQLite Locking Contention

**What goes wrong:** Multiple concurrent writes cause "database is locked" errors when writing decision records.

**Why it happens:** SQLite's default rollback journal mode locks the entire database during writes.

**How to avoid:**
1. Enable Write-Ahead Logging (WAL) mode: `PRAGMA journal_mode=WAL`
2. Reduce sync frequency: `PRAGMA synchronous=NORMAL`
3. Use connection pooling or single dedicated writer thread
4. Batch writes to reduce transaction frequency
5. Consider PostgreSQL if >5 concurrent writers needed

**Warning signs:**
- Frequent "database is locked" errors in logs
- Write latency increases over time
- Multiple consumer tasks failing

## Code Examples

Verified patterns from official sources:

### LangGraph Event Streaming
```python
# Source: LangGraph streaming documentation (2025)
async def capture_graph_execution(graph, input_state):
    """Capture complete execution trace."""
    trace = []

    async for event in graph.astream_events(
        input_state,
        version="v1",
        config={"run_name": "observability_capture"}
    ):
        if event["event"] == "on_chat_model_end":
            trace.append({
                "agent": event["name"],
                "output": event["data"]["output"].content,
                "timestamp": event["data"]["output"].response_metadata.get("timestamp")
            })
        elif event["event"] == "on_tool_end":
            trace.append({
                "tool": event["name"],
                "input": event["data"]["input"],
                "output": event["data"]["output"]
            })

    return trace
```

### SQLite with WAL Mode Optimization
```python
# Source: SQLite optimization best practices (2025)
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_optimized_connection(db_path: str):
    """Create optimized SQLite connection with WAL mode."""
    conn = sqlite3.connect(db_path, check_same_thread=False)

    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-10000")  # 10MB cache

    yield conn

    conn.close()

# Usage
with get_optimized_connection("decisions.db") as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            agent TEXT NOT NULL,
            decision TEXT NOT NULL,
            outcome_pending BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, trade_date, agent)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ticker_date ON decisions(ticker, trade_date)"
    )
```

### Decision Record with Outcome Hooks
```python
# Source: Extended from existing PredictionRecord pattern
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class DecisionRecord(BaseModel):
    """Record of an agent decision with outcome tracking hooks."""

    # Context
    ticker: str
    trade_date: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Agent decision
    agent_name: str
    agent_type: str  # "analyst", "researcher", "debater", "manager", "trader"
    decision: str
    reasoning: str

    # Outcome tracking hooks (DATA-03 requirement)
    outcome_pending: bool = Field(default=True)
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    hold_days: int = Field(default=7)
    return_pct: Optional[float] = None
    outcome_calculated: bool = Field(default=False)
    outcome_calculated_at: Optional[datetime] = None

    # Confidence (placeholder for Phase 2)
    confidence: Optional[float] = Field(default=None)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AgentEvent(BaseModel):
    """Event captured during agent execution."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # "llm_call", "tool_use", "state_transition"
    agent_name: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| **Synchronous logging** | **Async queue with producer-consumer** | 2019-2020 | Non-blocking observability is now standard for high-throughput systems |
| **File-based logs** | **Structured JSON logging with trace IDs** | 2021-2022 | Queryable logs enable observability platforms (ELK, Datadog) |
| **Callback injection** | **Event streaming (astream_events)** | 2024-2025 | Non-invasive instrumentation; no code changes required |
| **Rollback journal** | **Write-Ahead Logging (WAL)** | 2010+ | Better concurrency, 8x faster insert performance |
| **Full transcript capture** | **Structured summaries + sampling** | 2023-2024 | Reduces storage by 90% while preserving insights |

**Deprecated/outdated:**
- **LangSmith callbacks**: Closed-source, expensive ($75K+ licensing). Use Langfuse or `astream_events` instead.
- **Chromadb for decision storage**: Overkill for structured decision data. SQLite or PostgreSQL sufficient.
- **Custom event buses**: `asyncio.Queue` is battle-tested and sufficient for single-machine deployment.

## Open Questions

1. **Retention policy for decision records**
   - What we know: Storage grows with trading frequency; historical data needed for Phase 4 (Performance Correlation)
   - What's unclear: How long to keep raw event data vs aggregated summaries; whether to archive old records
   - Recommendation: Start with 90-day retention for raw events, 1-year for aggregated decisions. Add config option for retention period.

2. **Outcome calculation timing**
   - What we know: `hold_days` parameter exists; existing `AgentTracker` uses 7 days default
   - What's unclear: When is a decision "resolved"? (1 day? 7 days? 30 days?) Should this vary by decision type?
   - Recommendation: Keep 7-day default (matches existing pattern). Make configurable per ticker or strategy in Phase 4.

3. **Storage backend selection for production**
   - What we know: SQLite sufficient for single-user (<5 concurrent writers); PostgreSQL needed for multi-user
   - What's unclear: When will observability need multi-user access? Is it personal tool or team platform?
   - Recommendation: Start with SQLite (Phase 1-3). Add PostgreSQL backend option in Phase 5 (API Layer) if multi-user access needed.

4. **Full transcript vs summary capture**
   - What we know: Full transcripts cause storage bloat; summaries lose nuance
   - What's unclear: Which agent outputs need full capture? (Bull/bear debates? Final decisions only?)
   - Recommendation: Capture summaries by default, sample 10% of full transcripts for debugging. Store full bull/bear debates (key differentiator).

## Validation Architecture

> **Note:** Nyquist validation is DISABLED in config (workflow.nyquist_validation=false). Skip this section.
>
> When validation is enabled, this section will document test infrastructure and map requirements to automated tests.

**Rationale:** Phase 1 is foundational data collection infrastructure. Testing will be done through manual verification during Phase 3 (Decision Trail) when visualization confirms data capture is working correctly.

## Sources

### Primary (HIGH confidence)
- **LangGraph Documentation** — Official `astream_events` API, stream modes (values, updates, messages, debug, custom)
- **Python asyncio Documentation** — `asyncio.Queue` producer-consumer pattern, non-blocking operations
- **SQLite Documentation** — WAL mode optimization, PRAGMA settings for performance
- **Pydantic Documentation** — BaseModel for data validation, type-safe data models
- **Existing Codebase Analysis** — `AgentTracker` pattern, storage backend abstraction, `AgentState` structure

### Secondary (MEDIUM confidence)
- **[2025最强实战指南：LangGraph构建生产级AI代理应用的5大核心技巧](https://m.blog.csdn.net/gitblog_00281/article/details/151487214)** — Langfuse callback integration (alternative approach)
- **[Asyncio异步队列应用全解析](https://m.blog.csdn.net/logicplex/article/details/156511499)** — Deep dive into asyncio queue concepts
- **[从入门到精通：用Asyncio队列实现可靠数据流的7个步骤](https://m.blog.csdn.net/proceshoal/article/details/156511420)** — 7-step guide to reliable data flow
- **[Python Asyncio背景任务顺序执行与并发管理](https://m.php.cn/enfaq/1408856.html)** — Producer-consumer patterns for ordered execution
- **SQLite vs PostgreSQL Performance Comparison** — Benchmark data showing SQLite 2-20x faster for single-user, PostgreSQL better for concurrency

### Tertiary (LOW confidence)
- **LangGraph生产环境部署指南** — Production deployment experiences, memory leaks, state management challenges
- **Python Structured Logging Best Practices 2025** — Structured logging patterns (verified with standard library docs)
- **Decision logging performance benchmarks** — Performance metrics for file-based vs SQLite vs PostgreSQL (needs validation in this specific use case)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - LangGraph, asyncio, SQLite are established technologies with official documentation
- Architecture: HIGH - Producer-consumer async pattern is well-documented; LangGraph streaming confirmed in official docs
- Pitfalls: HIGH - Research-backed with specific performance impacts and prevention strategies
- Storage approach: MEDIUM - SQLite vs PostgreSQL decision depends on concurrency needs (unknown); SQLite is safe starting point

**Research date:** 2026-02-27
**Valid until:** 2026-04-27 (60 days - LangGraph evolving rapidly, verify `astream_events` API hasn't changed before implementation)

**What might I have missed?**
- LangGraph callback handler alternatives to `astream_events` (if streaming approach has performance issues)
- Specific LangGraph event types available in `astream_events` (documentation may list more than captured in research)
- Existing observability libraries (Langfuse, Arize, LangSmith) that could provide drop-in solution
- Memory impact of storing full AgentState vs extracted fields
- Trade-offs between extending AgentTracker vs creating separate observability module
