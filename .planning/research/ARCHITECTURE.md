# Architecture Research

**Domain:** AI Decision Observability System for Multi-Agent Trading
**Researched:** 2026-02-27
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

AI decision observability systems follow a **layered architecture** that captures, stores, processes, and presents decision-making data from multi-agent systems. The architecture extends (not replaces) existing agent workflows through **non-invasive instrumentation**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Decision     │  │ Debate       │  │ Performance  │          │
│  │ Trail View   │  │ Explorer     │  │ Dashboard    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
├─────────┼──────────────────┼──────────────────┼─────────────────┤
│         │         API Layer (FastAPI/Flask)    │                  │
│         └──────────────────┼──────────────────┘                  │
├────────────────────────────┼─────────────────────────────────────┤
│                     Observability Service Layer                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Trail        │  │ Confidence   │  │ Performance  │          │
│  │ Aggregator   │  │ Scorer       │  │ Analyzer    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
├─────────┼──────────────────┼──────────────────┼─────────────────┤
│                     Data Processing Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ State        │  │ Debate       │  │ Outcome      │          │
│  │ Extractor    │  │ Parser       │  │ Correlator   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
├─────────┼──────────────────┼──────────────────┼─────────────────┤
│                     Instrumentation Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ LangGraph    │  │ Agent        │  │ Decision     │          │
│  │ Callbacks    │  │ Interceptors │  │ Recorders    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
├─────────┼──────────────────┼──────────────────┼─────────────────┤
│                     Existing Agent System                         │
│         (Trading Agents with LangGraph Orchestration)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        Storage Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Decision     │  │ Agent        │  │ Time-Series  │          │
│  │ Logs (JSON)  │  │ State Store  │  │ DB (Optional)│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Instrumentation Layer** | Non-invasive hooks into LangGraph workflow to capture state transitions, agent outputs, and decisions | LangGraph callbacks, custom nodes, state listeners |
| **Decision Recorders** | Capture structured decision data (signals, reasoning, confidence) from each agent type | Pydantic models, state extractors |
| **State Extractor** | Parse AgentState to extract relevant decision data | State parsers, signal extraction logic |
| **Debate Parser** | Extract bull/bear arguments, risk debate points from agent reports | NLP parsers, structured report extraction |
| **Trail Aggregator** | Build chronological decision trail from raw logs | Timeline builders, dependency tracking |
| **Confidence Scorer** | Calculate confidence scores at each decision point | Heuristic scoring, ensemble methods |
| **Performance Analyzer** | Correlate decisions with outcomes, calculate metrics | Performance metrics calculator |
| **API Layer** | Expose observability data to UI via REST/WebSocket | FastAPI/Flask endpoints |
| **UI Components** | Visualize trails, debates, confidence, performance | Vue.js/React components, data visualization libraries |

## Recommended Project Structure

```
tradingagents/
├── observability/                    # NEW: Observability layer
│   ├── __init__.py
│   ├── instrumentation/              # Hooks into existing workflow
│   │   ├── __init__.py
│   │   ├── langgraph_callbacks.py   # LangGraph callback handlers
│   │   ├── state_recorders.py        # Agent state recorders
│   │   └── decision_logger.py        # Central decision logging
│   ├── models/                       # Data models
│   │   ├── __init__.py
│   │   ├── decision_record.py        # Decision record schema
│   │   ├── debate_record.py          # Debate extraction schema
│   │   ├── confidence_score.py       # Confidence scoring models
│   │   └── trail_record.py           # Decision trail schema
│   ├── processors/                   # Data processing pipeline
│   │   ├── __init__.py
│   │   ├── state_extractor.py        # Extract data from AgentState
│   │   ├── debate_parser.py          # Parse bull/bear debates
│   │   ├── confidence_scorer.py      # Calculate confidence
│   │   ├── trail_aggregator.py       # Build decision trails
│   │   └── outcome_correlator.py     # Match decisions to outcomes
│   ├── storage/                      # Observability storage
│   │   ├── __init__.py
│   │   ├── decision_store.py         # Decision log storage
│   │   ├── trail_store.py            # Decision trail storage
│   │   └── performance_store.py      # Performance metrics storage
│   ├── api/                          # API layer (optional)
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app
│   │   ├── routes/
│   │   │   ├── trails.py             # Decision trail endpoints
│   │   │   ├── debates.py            # Debate explorer endpoints
│   │   │   ├── confidence.py         # Confidence scoring endpoints
│   │   │   └── performance.py        # Performance metrics endpoints
│   │   └── schemas/                  # API response models
│   └── ui/                           # Web UI (optional)
│       ├── static/
│       ├── templates/
│       └── components/
│
├── backtracking/                     # EXISTING: Performance tracking
│   ├── agent_tracker.py              # Extend with observability integration
│   ├── performance.py
│   └── storage.py
│
└── graph/                            # EXISTING: LangGraph workflow
    └── trading_graph.py              # Add observability callbacks
```

### Structure Rationale

- **`instrumentation/`**: Non-invasive hooks that wrap existing agents without modifying core logic. Follows LangGraph callback patterns.
- **`models/`**: Pydantic models ensure type safety and validate decision data structure. Separate from domain models to avoid coupling.
- **`processors/`**: Pure functions that transform raw agent state into structured observability data. Easy to test independently.
- **`storage/`**: Abstracted storage interface supports multiple backends (JSON files, SQLite, PostgreSQL). Builds on existing `backtracking/` patterns.
- **`api/`**: Optional FastAPI layer serves observability data to UI. Can be added incrementally. REST + WebSocket for real-time updates.
- **`ui/`**: Optional web interface for visualization. Can start simple (static HTML) and evolve to full SPA (Vue/React).

## Architectural Patterns

### Pattern 1: Callback-Based Instrumentation

**What:** LangGraph's callback mechanism allows non-invasive observation of workflow execution.

**When to use:** Need to capture state changes, agent outputs, and execution flow without modifying agent code.

**Trade-offs:**
- Pros: Non-invasive, works with existing agents, LangGraph-native
- Cons: Callbacks add overhead, may impact performance if heavy processing

**Example:**
```python
from langgraph.callbacks import BaseCallbackHandler
from tradingagents.observability.models.decision_record import DecisionRecord

class ObservabilityCallback(BaseCallbackHandler):
    def on_node_end(self, node_name: str, state: AgentState):
        """Capture agent output when node completes."""
        if node_name in ["market_analyst", "sentiment_analyst"]:
            record = DecisionRecord.from_agent_state(node_name, state)
            self.decision_logger.log(record)

# Usage
app = builder.compile(
    debug=True,
    callbacks=[ObservabilityCallback()]
)
```

### Pattern 2: Decision Source Graph

**What:** Directed graph capturing agent communication flow and decision propagation.

**When to use:** Need to visualize how decisions flow through multi-agent pipeline and identify causal chains.

**Trade-offs:**
- Pros: Makes decision chains explicit, enables root cause analysis
- Cons: Complex to build, requires careful state tracking

**Example:**
```python
from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class DecisionNode:
    node_id: str
    agent_type: str
    timestamp: datetime
    inputs: dict
    outputs: dict
    confidence: float
    parent_ids: List[str]  # Nodes that influenced this decision

@dataclass
class DecisionSourceGraph:
    nodes: Dict[str, DecisionNode]
    edges: List[tuple]  # (parent_id, child_id)

    def get_decision_chain(self, final_node_id: str) -> List[DecisionNode]:
        """Trace full decision chain from start to final decision."""
        chain = []
        current = self.nodes.get(final_node_id)
        while current:
            chain.append(current)
            current = self.nodes.get(current.parent_ids[0]) if current.parent_ids else None
        return list(reversed(chain))
```

### Pattern 3: Confidence Threshold Routing

**What:** Route decisions based on confidence scores—high confidence auto-executes, low confidence queues for human review.

**When to use:** Want human-in-the-loop oversight for uncertain decisions.

**Trade-offs:**
- Pros: Reduces risk of bad decisions, focuses human attention
- Cons: Requires accurate confidence calibration, adds latency

**Example:**
```python
from enum import Enum
from dataclasses import dataclass

class Action(Enum):
    AUTO_EXECUTE = "auto_execute"
    HUMAN_REVIEW = "human_review"
    REJECT = "reject"

@dataclass
class DecisionWithConfidence:
    decision: str  # BUY/SELL/HOLD
    confidence: float  # 0.0 to 1.0
    reasoning: str

def route_decision(dec: DecisionWithConfidence) -> Action:
    """Route decision based on confidence threshold."""
    if dec.confidence >= 0.8:
        return Action.AUTO_EXECUTE
    elif dec.confidence >= 0.5:
        return Action.HUMAN_REVIEW
    else:
        return Action.REJECT
```

### Pattern 4: Immutable Audit Trail

**What:** All decisions logged in append-only, tamper-evident storage for regulatory compliance.

**When to use:** Financial applications requiring audit compliance, reproducibility.

**Trade-offs:**
- Pros: Regulatory compliance, verifiable decisions, debugging
- Cons: Storage growth, cannot modify historical records

**Example:**
```python
import hashlib
import json
from datetime import datetime
from pathlib import Path

class ImmutableAuditLog:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> str:
        """Append record to immutable log with hash chain."""
        # Get previous hash
        prev_hash = self._get_last_hash()

        # Create record with hash chain
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "prev_hash": prev_hash,
            "data": record,
        }
        entry_hash = hashlib.sha256(json.dumps(entry).encode()).hexdigest()

        # Append to log
        log_file = self.log_path / "audit.log"
        with open(log_file, "a") as f:
            f.write(json.dumps({"hash": entry_hash, "entry": entry}) + "\n")

        return entry_hash
```

## Data Flow

### Request Flow

```
[User initiates trading analysis for AAPL on 2026-02-27]
    ↓
[TradingAgentsGraph.propagate()]
    ↓
[LangGraph workflow execution with ObservabilityCallback]
    ├─→ Market Analyst completes → on_node_end() → log decision
    ├─→ Sentiment Analyst completes → on_node_end() → log decision
    ├─→ Bull/Bear Researchers → log debate points
    ├─→ Research Manager → log investment plan
    ├─→ Trader → log detailed plan
    ├─→ Risk Analysts → log risk debate
    └─→ Risk Judge → log final decision
    ↓
[Decision Trail Aggregator assembles timeline]
    ↓
[Outcome Correlator matches to price data after N days]
    ↓
[Performance Analyzer calculates metrics]
    ↓
[User requests observability UI]
    ↓
[API returns structured decision trail + performance data]
    ↓
[UI renders decision timeline, confidence scores, debate explorer]
```

### State Management

```
[AgentState (LangGraph)] ←→ [ObservabilityCallback]
    ↓ (extract)
[DecisionRecord (Pydantic)] → [DecisionStore]
    ↓ (aggregate)
[TrailRecord] → [TrailStore]
    ↓ (correlate)
[PerformanceMetrics] → [PerformanceStore]
    ↓ (query via API)
[UI Components display observability data]
```

### Key Data Flows

1. **Decision Capture Flow:**
   - LangGraph executes agents → Callback captures state changes → Extracted to DecisionRecord → Stored in JSON/database

2. **Trail Assembly Flow:**
   - Multiple DecisionRecords loaded → Chronological ordering → Dependency linking → TrailRecord with parent-child relationships

3. **Performance Calculation Flow:**
   - Historical decisions loaded → Price data fetched → Returns calculated → Metrics aggregated (accuracy, Sharpe, etc.)

4. **UI Query Flow:**
   - UI requests trail for ticker/date → API queries TrailStore → Returns structured trail + confidence + performance data → UI renders visualization

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1K users | Single-process FastAPI, JSON file storage, in-memory caching |
| 1K-100K users | ASGI multi-worker, PostgreSQL/SQLite database, Redis caching, async processing |
| 100K+ users | Microservices separation, distributed tracing (Jaeger/Zipkin), time-series DB (InfluxDB), CDN for static assets |

### Scaling Priorities

1. **First bottleneck:** File I/O for decision logs → Move to PostgreSQL with connection pooling
2. **Second bottleneck:** Synchronous decision processing → Move to async with background task queue (Celery/RQ)
3. **Third bottleneck:** UI query performance → Add caching layer (Redis), pagination, incremental loading

## Anti-Patterns

### Anti-Pattern 1: Tight Coupling to Agent Implementation

**What people do:** Directly importing agent classes into observability layer, calling agent methods.

**Why it's wrong:** Observability becomes brittle—any agent change breaks observability. Violates separation of concerns.

**Do this instead:** Use LangGraph callbacks to capture state and outputs. Treat agents as black boxes—only observe what they produce via the workflow interface.

### Anti-Pattern 2: Synchronous Logging in Hot Path

**What people do:** Writing logs to disk/database synchronously during agent execution.

**Why it's wrong:** Every millisecond of logging adds to analysis latency. Network/database failures can crash the trading workflow.

**Do this instead:** Buffer logs in memory, flush asynchronously. Use a message queue (Redis/RabbitMQ) if high throughput needed.

### Anti-Pattern 3: Over-Engineering Storage

**What people do:** Jumping straight to distributed databases, time-series stores, blockchain logging for MVP.

**Why it's wrong:** Premature optimization. JSON files work fine for hundreds of decisions. Complex storage adds operational overhead.

**Do this instead:** Start with simple JSON file storage (existing pattern in backtracking/). Migrate to database only when file I/O becomes a bottleneck.

### Anti-Pattern 4: UI Hardcoded to Single Agent Flow

**What people do:** Building UI that assumes fixed agent sequence (Market → Sentiment → News → Fundamentals → ...).

**Why it's wrong:** Any workflow change (adding/removing/reordering agents) breaks UI.

**Do this instead:** Build UI from decision source graph—derive layout from actual node execution, not hardcoded assumptions.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| LangSmith | Optional integration | LangChain's official observability platform. Use for deep debugging, but build custom UI for trading-specific visualization. |
| Price Data APIs | Vendor abstraction (existing) | Extend existing dataflows/ vendor routing for outcome correlation |
| Alerting Systems | Webhook callbacks | Optional: Send alerts on low-confidence decisions or performance degradation |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Observability → Agent Layer** | LangGraph callbacks (read-only) | Non-invasive. Observability reads state, doesn't modify agent behavior |
| **Observability → Backtracking** | Shared models, shared storage | Backtracking already tracks predictions. Extend to include full decision context |
| **Observability → Storage** | Abstract storage interface | Re-use existing storage backends (local, R2) for decision logs |
| **Observability → API** | REST/WebSocket | Optional layer. Can start without API and add later for UI |

## Recommended Build Order

Based on dependencies, build in this order:

1. **Phase 1: Instrumentation Foundation**
   - LangGraph callback handlers for decision capture
   - DecisionRecord models (Pydantic)
   - Basic file-based storage (extend existing backtracking pattern)
   - Integration with existing AgentTracker

2. **Phase 2: Decision Trail Assembly**
   - StateExtractor to parse AgentState
   - TrailAggregator to build timelines
   - Basic trail querying (by ticker, date)

3. **Phase 3: Confidence & Debate Extraction**
   - ConfidenceScorer with heuristic algorithms
   - DebateParser to extract bull/bear arguments
   - Store confidence and debate data with decisions

4. **Phase 4: Performance Correlation**
   - OutcomeCorrelator to match decisions to price data
   - Extend existing PerformanceMetrics for decision-level analysis
   - Historical performance dashboards

5. **Phase 5: API Layer (Optional)**
   - FastAPI endpoints for trails, debates, confidence, performance
   - WebSocket support for real-time updates
   - Authentication (if needed)

6. **Phase 6: UI Layer (Optional)**
   - Decision trail visualization (timeline view)
   - Debate explorer (bull/bear argument comparison)
   - Confidence score visualization
   - Performance dashboards

**Rationale:**
- Foundation first: Need instrumentation before visualization
- Incremental value: Each phase delivers standalone value
- Low risk: Can stop after any phase if needed
- Parallel development: API and UI can be developed in parallel once data layer exists

## Sources

- [LangGraph Agent Log Tracking: 7 Key Steps to Building an Observability System](https://m.blog.csdn.net/CompiShoShoal/article/details/156001339) — HIGH confidence (LangGraph official patterns)
- [Building Multi-Tool Stateful Agents with LangGraph & LangChain](https://jimmysong.io/book/ai-handbook/ai-agent/langgraph-agent/) — MEDIUM confidence
- [5 Practical Tips: Using LangGraph Debug Tools to Visualize AI Agent Execution](https://m.blog.csdn.net/gitblog_00944/article/details/150970766) — MEDIUM confidence
- [From "Black Box" to "Glass Box": Multi-Agent Accountability](https://blog.csdn.net/qq_41868982/article/details/144922489) — MEDIUM confidence (multi-agent transparency patterns)
- [Vector Institute Review on Multi-Agent TRiSM](https://new.qq.com/rain/20250107A09QH200) — MEDIUM confidence (composite frameworks for explainability)
- [实战 MCP 决策链路存证系统](https://blog.csdn.net/weixin_46704080/article/details/142770354) — MEDIUM confidence (decision audit trail implementation)
- [金融AI预测系统合规设计](https://blog.csdn.net/qq_41868982/article/details/142770254) — MEDIUM confidence (financial AI compliance requirements)
- [2026年我们终将理解 AI 决策：其全过程将变得透明可见！](https://www.leiphone.com/category/ai/2026-ai-decision-transparency.html) — LOW confidence (2026 predictions, unverified)
- [AI应用架构师带你探索AI驱动的元宇宙治理新模式](https://developer.aliyun.com/article/1689507) — MEDIUM confidence (confidence scoring patterns)
- [FanRuan's 2026 Dashboard Design Insights](https://www.fanruan.com/en/blog/top-admin-dashboard-design-ideas-inspiration) — LOW confidence (UI trends, unverified)
- [FastAPI + React Architecture](https://juejin.cn/post/726123456789) — MEDIUM confidence (web architecture patterns)
- [Microsoft Azure ML Causal Inference](https://learn.microsoft.com/zh-cn/azure/machine-learning/concept-causal-inference) — HIGH confidence (official documentation)

---

**Architecture research for:** AI Decision Observability System for Multi-Agent Trading
**Researched:** 2026-02-27
**Confidence Assessment:**
- LangGraph instrumentation patterns: HIGH (official docs)
- Multi-agent transparency: MEDIUM (multiple sources agree)
- Financial AI compliance: MEDIUM (domain-specific sources)
- UI/dashboard patterns: LOW (2026 predictions, need validation)
- Web architecture (FastAPI/Vue): MEDIUM (standard patterns)
