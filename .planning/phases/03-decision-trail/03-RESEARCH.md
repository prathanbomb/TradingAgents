# Phase 3: Decision Trail - Research

**Researched:** 2026-02-27
**Domain:** Decision Trail Visualization & Timeline Analysis
**Confidence:** MEDIUM

## Summary

Phase 3 implements the Decision Trail feature, enabling users to view the complete timeline of decision flow from data input through analysis, debate, and final recommendation. This phase builds on Phase 1's data collection infrastructure (DecisionRecord, AgentEvent models) and Phase 2's confidence tracking to provide a comprehensive view of how decisions emerge from the multi-agent system.

**Primary recommendation:** Implement decision trails using SQLite time-series queries with chronological aggregation, building timeline views from existing DecisionRecord and AgentEvent data, and creating a TrailBuilder class that constructs causal chains from the agent execution flow.

The core challenge is organizing the already-captured decision events into a coherent timeline that shows both chronological order and causal relationships. Research shows that effective decision trails require: (1) proper time-series indexing for efficient queries, (2) chronological event aggregation by run_id, (3) causal chain reconstruction from state transitions, and (4) progressive disclosure to avoid information overload.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLite | 3.40+ | Time-series decision trail storage | Already in use from Phase 1, efficient time-range queries with proper indexes |
| Pydantic | 2.0+ | Trail data models | Consistent with existing DecisionRecord/AgentEvent models |
| NumPy | 1.24+ | Time-series data processing | Already in use (Phase 2), efficient array operations for timeline aggregation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | Timeline timestamp processing | Standard library, ISO format parsing |
| uuid | stdlib | Trail identifier generation | Standard library, unique trail IDs |
| typing | stdlib | Type hints for trail models | Standard library, TYPE_CHECKING for circular imports |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLite time-series queries | TimescaleDB | TimescaleDB provides better time-series optimization but adds external dependency; SQLite with proper indexes is sufficient for single-user scale |
| Custom TrailBuilder | LangGraph built-in tracing | LangGraph tracing requires external LangSmith integration; custom approach gives full control over trail format and works offline |

**Installation:**
```bash
# No additional packages required - all dependencies already installed
# SQLite, Pydantic, NumPy already in use from Phases 1-2
```

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/observability/
├── trail/
│   ├── __init__.py
│   ├── builder.py           # TrailBuilder for constructing decision trails
│   ├── models.py            # DecisionTrail, TrailNode, TrailEdge models
│   └── queries.py           # Trail query interface for filtering/search
└── storage/
    └── sqlite_backend.py    # Extended with trail query methods
```

### Pattern 1: Trail Aggregation by run_id

**What:** Group all DecisionRecord and AgentEvent objects by run_id to reconstruct the complete execution timeline for a single trading analysis.

**When to use:** When displaying the complete decision trail for a specific ticker/date analysis.

**Example:**
```python
# Source: Based on Phase 1 data model design
class TrailBuilder:
    """Builds decision trails from stored events and records."""

    def build_trail(self, run_id: str) -> DecisionTrail:
        """Build a complete decision trail for a run.

        Args:
            run_id: Run identifier grouping related events

        Returns:
            DecisionTrail with chronological events and causal edges
        """
        # Fetch all events and records for this run_id
        events = self.store.get_agent_events(run_id=run_id)
        records = self.store.get_decision_records_by_run_id(run_id=run_id)

        # Sort by timestamp to establish chronological order
        all_items = sorted(
            events + records,
            key=lambda x: x.timestamp
        )

        # Build causal chain from state transitions
        return self._build_causal_chain(all_items)
```

### Pattern 2: Causal Chain Reconstruction

**What:** Use AgentEvent.state_transition events (from_state → to_state) to construct a directed graph showing the causal flow between agent decisions.

**When to use:** When visualizing the decision path from data input through analysis to final recommendation.

**Example:**
```python
# Source: Based on AgentEvent state_transition pattern (Phase 1)
def _build_causal_chain(
    self,
    items: List[Union[AgentEvent, DecisionRecord]]
) -> DecisionTrail:
    """Reconstruct causal chain from state transitions.

    State transition events capture the LangGraph node traversal,
    showing which agent called which and in what order.
    """
    nodes = []
    edges = []

    for item in items:
        if isinstance(item, AgentEvent) and item.event_type == "state_transition":
            # Create edge from from_state to to_state
            edges.append(TrailEdge(
                source=item.from_state,
                target=item.to_state,
                timestamp=item.timestamp,
                agent_name=item.agent_name,
            ))
        elif isinstance(item, DecisionRecord):
            # Create node for this agent decision
            nodes.append(TrailNode(
                agent_name=item.agent_name,
                decision=item.decision,
                confidence=item.confidence,
                reasoning=item.reasoning[:200],  # Truncate for display
                timestamp=item.timestamp,
            ))

    return DecisionTrail(nodes=nodes, edges=edges, run_id=run_id)
```

### Pattern 3: Time-Series Query Optimization

**What:** Use SQLite indexes on (run_id, timestamp) for efficient chronological queries and time-range filtering.

**When to use:** When querying decision trails with date ranges or filtering by specific runs.

**Example:**
```python
# Source: SQLite time-series optimization best practices (2025-2026)
# Index definition (already in Phase 1 schema):
# CREATE INDEX idx_run_id_events ON agent_events(run_id)
# CREATE INDEX idx_run_id_decisions ON decision_records(run_id)

# Query pattern for efficient trail retrieval:
def get_trail_events(
    self,
    run_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get events for a trail with optional time filtering.

    Uses index on (run_id, timestamp) for efficient queries.
    """
    query = """
        SELECT * FROM agent_events
        WHERE run_id = ?
    """
    params = [run_id]

    if start_time:
        query += " AND timestamp >= ?"
        params.append(start_time)

    if end_time:
        query += " AND timestamp <= ?"
        params.append(end_time)

    query += " ORDER BY timestamp ASC"

    cursor = self.conn.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

### Anti-Patterns to Avoid

- **Synchronous trail building:** Don't build trails on the critical path of trading analysis. Trail construction should be asynchronous and on-demand.
- **Full reasoning text in timeline:** Don't show full agent reasoning (1000+ chars) in timeline view. Use truncated summaries with "show more" expansion.
- **Missing causal links:** Don't just list events chronologically without showing which agent called which. State transition events are critical for understanding flow.
- **N+1 query pattern:** Don't query separately for each agent's events. Fetch all events for a run_id in a single query, then group in memory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-series sorting | Custom sort logic | SQLite ORDER BY timestamp | Database index makes sorting 4x faster than in-memory Python sort |
| UUID generation | Custom ID schemes | uuid.uuid4() or uuid.uuid5() | Standard library, collision-resistant, already in use |
| Timestamp parsing | Custom datetime parsing | datetime.fromisoformat() | Standard library, handles ISO format natively |
| Type validation | Manual type checking | Pydantic BaseModel | Already in use, provides validation and JSON serialization |

**Key insight:** The existing Phase 1 infrastructure (DecisionRecord, AgentEvent, SQLite storage) provides 80% of what's needed for decision trails. Phase 3 is primarily about aggregation and presentation, not new data capture.

## Common Pitfalls

### Pitfall 1: Information Overload in Timeline View

**What goes wrong:** Users see a wall of chronological events (LLM calls, tool uses, state transitions) and cannot identify which decisions matter.

**Why it happens:** Treating all events as equally important in the timeline, showing full reasoning text, and not highlighting key decision points.

**How to avoid:**
- Show summary view first: only DecisionRecord nodes (agent decisions) with confidence scores
- Provide "show details" expansion for AgentEvent (LLM calls, tool uses)
- Highlight decision-changing events (state transitions that affect final recommendation)
- Use visual encoding (color, size) to indicate confidence and decision importance

**Warning signs:** Timeline view requires scrolling through 100+ events to understand what happened.

### Pitfall 2: Missing run_id Grouping

**What goes wrong:** Decision trail shows events from multiple analysis runs mixed together, making it impossible to understand a single decision flow.

**Why it happens:** Not filtering by run_id when querying events, or not setting run_id consistently during data collection.

**How to avoid:**
- Always generate and store run_id at the start of graph.propagate()
- Pass run_id through all agent calls via AgentState
- Query with WHERE run_id = ? for all trail queries
- Validate run_id presence in DecisionRecord and AgentEvent

**Warning signs:** Timeline shows agents with the same name appearing multiple times without clear separation.

### Pitfall 3: Inefficient Time-Series Queries

**What goes wrong:** Trail queries take seconds to load as database grows, making UI feel sluggish.

**Why it happens:** Missing indexes on (run_id, timestamp), using OR conditions instead of AND, or filtering in Python instead of SQL.

**How to avoid:**
- Ensure compound index on (run_id, timestamp) exists
- Use WHERE run_id = ? AND timestamp >= ? AND timestamp <= ?
- Let SQLite do the filtering and sorting (ORDER BY timestamp ASC)
- Avoid fetching all rows and filtering in Python

**Warning signs:** Query time increases linearly with database size (should be constant with proper indexes).

### Pitfall 4: Broken Causal Chain Links

**What goes wrong:** Trail shows events chronologically but doesn't show which agent output influenced the next agent's decision.

**Why it happens:** Not capturing or displaying state_transition events, or not linking DecisionRecord reasoning to previous agent outputs.

**How to avoid:**
- Ensure AgentEvent.create_state_transition() is called for every LangGraph edge
- Display causal edges alongside chronological nodes in trail view
- Show "in response to" links connecting agent decisions to previous outputs
- Validate that from_state and to_state are populated in state_transition events

**Warning signs:** Users cannot trace how the Bull Researcher's argument influenced the Investment Judge's decision.

## Code Examples

Verified patterns from official sources:

### Building a Decision Trail

```python
# Source: Based on Phase 1 AgentEvent and DecisionRecord models
from tradingagents.observability.trail import TrailBuilder, DecisionTrail

# Initialize trail builder with storage backend
builder = TrailBuilder(store=decision_store)

# Build complete trail for a specific analysis run
trail: DecisionTrail = builder.build_trail(run_id="abc123")

# Access chronological events
for node in trail.nodes:
    print(f"{node.timestamp}: {node.agent_name} -> {node.decision}")

# Access causal edges
for edge in trail.edges:
    print(f"{edge.source} --> {edge.target} ({edge.agent_name})")
```

### Querying Trails with Filters

```python
# Source: SQLite query optimization best practices (2025)
from tradingagents.observability.trail import TrailQuery

# Initialize query interface
trail_query = TrailQuery(store=decision_store)

# Query trails for specific ticker and date range
trails = trail_query.get_trails(
    ticker="AAPL",
    start_date="2026-01-01",
    end_date="2026-01-31",
)

# Filter by agent type
analyst_decisions = trail_query.get_trail_nodes(
    run_id="abc123",
    agent_type="analyst",
)
```

### Timeline Aggregation

```python
# Source: Time-series aggregation patterns (libSQL 2025)
def aggregate_timeline_by_agent(
    events: List[Union[AgentEvent, DecisionRecord]]
) -> Dict[str, List[Dict]]:
    """Aggregate events by agent for timeline view.

    Groups events chronologically within each agent's timeline.
    """
    timeline = {}

    for event in sorted(events, key=lambda x: x.timestamp):
        agent = event.agent_name

        if agent not in timeline:
            timeline[agent] = []

        timeline[agent].append({
            "timestamp": event.timestamp,
            "type": event.event_type if hasattr(event, "event_type") else "decision",
            "data": event.decision if hasattr(event, "decision") else event.data,
        })

    return timeline
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate decision/event stores | Unified trail aggregation by run_id | 2025-2026 | Simplifies trail construction, improves query performance |
| Chronological-only views | Causal graph + chronological timeline | 2025-2026 | Users can see both WHEN decisions happened and WHY |
| Full event logs | Progressive disclosure (summary → details) | 2025 | Reduces information overload, improves UX |

**Deprecated/outdated:**
- **LangSmith-only tracing:** Required external service and API keys. Local trail building with SQLite gives same functionality without dependencies.
- **Flat event logs:** Without run_id grouping or causal links, impossible to reconstruct decision flow.

## Open Questions

1. **Visualization approach for causal chains**
   - What we know: Research shows Network (pyvis) and D3.js are popular for decision path visualization. LangGraph has built-in `get_graph().draw_mermaid_png()`.
   - What's unclear: Whether to implement visualization in Phase 3 or defer to UI phase. Text-based causal chain may suffice for initial implementation.
   - Recommendation: Start with text-based timeline showing causal links (e.g., "Bull Researcher → Investment Judge"). Add graph visualization in Phase 6 (UI Layer) if needed.

2. **Trail retention policy**
   - What we know: SQLite can handle millions of records with proper indexes. Storage cost is minimal for text data.
   - What's unclear: How long to keep trails. Indefinite retention vs. time-based expiration (e.g., 90 days).
   - Recommendation: Implement indefinite retention for v1. Add configurable retention policy in Phase 5 (Performance Correlation) when storage growth becomes a concern.

3. **Real-time trail updates**
   - What we know: Phase 1 uses async pipeline with asyncio.Queue for non-blocking storage. Trails are built after data is stored.
   - What's unclear: Whether to support real-time trail streaming (updates as events happen) vs. on-demand trail building.
   - Recommendation: On-demand trail building for v1. Real-time streaming requires WebSocket/SSE infrastructure (Phase 5 - API Layer).

## Validation Architecture

> Skip this section - workflow.nyquist_validation is not set in config.json

## Sources

### Primary (HIGH confidence)
- **Existing Phase 1 Implementation** — DecisionRecord, AgentEvent models with run_id grouping, timestamp indexing
- **Existing Phase 2 Implementation** — ConfidenceHistory query patterns for time-series aggregation
- **SQLite Documentation** — Time-series optimization with indexes, ORDER BY performance
- **Pydantic Documentation** — BaseModel validation and JSON serialization

### Secondary (MEDIUM confidence)
- **LangGraph Documentation (2025-2026)** — Decision trace capabilities, state transition events, `graph.stream(trace=True)`
- **Decision Trail Visualization Research (2025-2026)** — Network (pyvis) for interactive decision paths, progressive disclosure patterns
- **SQLite Time Series Best Practices (2025)** — libSQL optimization strategies, compound indexes, query patterns
- **CSDN Blog: Decision Path Visualization (September 2025)** — Python implementation patterns for decision trail visualization
- **CSDN Blog: Python Database Risk Identification (March 2025)** — Query pattern analysis and audit trail implementation

### Tertiary (LOW confidence)
- **D3 Timeline Guide (November 2025)** — JavaScript-based visualization (not applicable for Python backend)
- **Observability Trends 2026** — General industry trends, not specific to decision trail implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use from Phases 1-2, verified with existing codebase
- Architecture: MEDIUM - Trail aggregation patterns are well-established (SQLite time-series, run_id grouping), but causal chain visualization needs validation during implementation
- Pitfalls: MEDIUM - Based on research findings and Phase 1-2 implementation experience, information overload is confirmed risk from multiple sources

**Research date:** 2026-02-27
**Valid until:** 2026-03-29 (30 days - stack is stable but visualization patterns may evolve)

## Phase Requirements Mapping

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRAIL-01 | Users can view a timeline of decision flow from data input to final recommendation | TrailBuilder.build_trail() aggregates DecisionRecord and AgentEvent by run_id, sorted chronologically |
| TRAIL-02 | Timeline shows each agent's action and output in chronological order | SQLite ORDER BY timestamp ASC with proper indexing; existing AgentEvent captures all agent actions |
| TRAIL-03 | Users can filter and search through past decision trails | TrailQuery interface with ticker, date range, agent_type filters building on existing query patterns |
| TRAIL-04 | System displays the causal chain from data → analysis → debate → decision | state_transition events (from_state → to_state) enable causal chain reconstruction; existing AgentEvent model supports this |
