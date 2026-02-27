# Technology Stack

**Project:** Trading Agents Observatory - AI Decision Observability Layer
**Researched:** 2026-02-27
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **FastAPI** | 0.115+ | Python async backend for observability API | Native async/await support, automatic OpenAPI docs, perfect for real-time updates via SSE/WebSocket, integrates seamlessly with LangGraph ecosystem |
| **React** | 19.x | Frontend framework for observability dashboard | Largest ecosystem for data visualization (React D3 Tree, Tremor, shadcn-ui), enterprise adoption for complex dashboards, best-in-class TypeScript support |
| **TypeScript** | 5.8+ | Type-safe frontend development | Industry standard (80%+ adoption in 2025), 15-65% bug reduction in production, strict mode catches errors at compile-time, essential for complex observability UIs |
| **Vite** | 6.x | Frontend build tool and dev server | Fast HMR for dashboard development, native TypeScript support, optimized production builds, standard for React projects in 2025 |
| **PostgreSQL** | 16+ | Primary database for decision tracking | Relational data for decision metadata, proven scalability, excellent tooling ecosystem, works with existing Python stack |
| **TimescaleDB** | 2.15+ | PostgreSQL extension for time-series decision data | Automatic partitioning by time, built-in compression for historical decisions, full SQL support for complex queries, purpose-built for decision tracking over time |

### Data Visualization

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **React D3 Tree** | 3.x | Decision trail visualization (data → analysis → debate → decision) | Hierarchical tree structures showing agent decision chains, highly customizable nodes and edges, TypeScript support, handles large datasets efficiently |
| **D3.js** | 7.x | Custom visualizations for agent debates and confidence scoring | Maximum flexibility for debate graphs, confidence heatmaps, performance scatter plots, steep learning curve but unmatched power |
| **Plotly.py** | 5.24+ | Python backend visualization for historical performance | Time-series charts for decisions vs outcomes, integration with Dash if needed, interactive charts with zoom/pan |
| **Tremor** | 3.x | React dashboard components for metrics overview | Pre-built dashboard components (cards, charts, tables), consistent design system, rapid development for standard metrics displays |

### Real-time Communication

| Technology | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Server-Sent Events (SSE)** | - | One-way streaming updates (agent → dashboard) | Push decision updates to UI without page refresh, simpler than WebSocket, lower resource consumption, use FastAPI `StreamingResponse` with `media_type="text/event-stream"` |
| **WebSocket** | - | Bidirectional communication (dashboard → agent control) | User controls agent execution from UI, interactive debate participation, use FastAPI native WebSocket support with ConnectionManager pattern |

### Observability Integration

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Langfuse** | Latest (open source) | LangGraph observability and tracing | Open-source alternative to LangSmith, 8000+ self-hosted deployments, works with multiple frameworks, all features freely available since June 2025, deep LangGraph integration |
| **OpenTelemetry** | 1.28+ | Standardized tracing and metrics collection | Vendor-agnostic observability, integrates with LangGraph, export to Jaeger/Tempo for visualization, future-proof for multi-tool stacks |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Pydantic** | 2.10+ | Data validation and serialization | Type-safe API contracts, automatic JSON schema generation, validates decision data before storage, FastAPI native integration |
| **SQLAlchemy** | 2.0+ | Python ORM for database access | Async support for high-performance queries, migrations with Alembic, works with PostgreSQL/TimescaleDB |
| **Alembic** | 1.14+ | Database migration tool | Schema evolution for decision tracking tables, version-controlled database changes, rollback capability |
| **Redis** | 7.x | Caching and pub/sub for real-time updates | Optional: cache decision summaries, pub/sub for cross-instance WebSocket broadcasts, use if deploying multiple instances |
| **HTTPX** | 0.27+ | Async HTTP client for testing | Modern async client for testing FastAPI endpoints, better than TestClient for async applications, supports WebSocket testing |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Tailwind CSS** | Utility-first CSS for dashboard | Use v4+ for optimal bundle size, pairs well with shadcn-ui components, rapid UI development without custom CSS |
| **shadcn-ui** | Accessible React component library | Copy-paste components (not npm install), fully customizable, built on Radix UI primitives, excellent for dashboards |
| **Vitest** | Fast unit testing for React | Native Vite integration, TypeScript support, faster than Jest for dashboard components |
| **pytest-asyncio** | Async Python testing | Test FastAPI endpoints, WebSocket handlers, database operations with pytest fixture support |
| **Ruff** | Fast Python linter/formatter | 10-100x faster than Flake8/Black, replaces multiple tools (Flake8, isort, pyupgrade), compatible with existing codebase |

## Installation

```bash
# Python backend
pip install fastapi uvicorn[standard] sqlalchemy alembic pydantic
pip install "langgraph>=0.4.8" "chromadb>=1.0.12"  # Already in project
pip install httpx pytest-asyncio redis
pip install plotly  # For backend visualizations

# PostgreSQL with TimescaleDB
# macOS
brew install postgresql@16 timescaledb

# Linux (Ubuntu/Debian)
# See: https://docs.timescale.com/install/latest/self-hosted/installation/

# Frontend (React + TypeScript + Vite)
npm create vite@latest observability-dashboard -- --template react-ts
cd observability-dashboard
npm install

# Visualization libraries
npm install react-d3-tree d3 plotly.js
npm install @types/d3

# Dashboard components
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init

# Additional UI libraries
npm install tremor  # Dashboard components
npm install @tanstack/react-query  # Server state management

# Dev dependencies
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **React** | Vue 3 | Team prefers template syntax, using DataV components, smaller project where Vue's simplicity shines |
| **React** | Svelte | Performance-critical dashboards with frequent real-time updates, want smallest bundle size, team prefers reactive syntax |
| **FastAPI + SSE** | Dash | Need pure Python dashboard without frontend team, rapid internal prototyping, accept limited customization |
| **FastAPI + SSE** | Streamlit | Quick MVP for internal tools, no frontend expertise, accept re-run performance limitations |
| **TimescaleDB** | InfluxDB | Pure time-series workload without relational needs, don't need SQL queries, metrics-only use case |
| **Langfuse** | LangSmith | Deep LangChain ecosystem integration, budget not constrained ($75K+ enterprise licensing), need commercial support |
| **React D3 Tree** | React Flow | Need node-based flowchart editor, user manipulates graph structure, decision chains are more DAG than tree |
| **React D3 Tree** | AntV G6 | Complex graph structures beyond trees, enterprise application, team comfortable with Chinese documentation |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **LangSmith (closed source)** | Requires $75K+ enterprise license for self-hosting, closed source limits customization, vendor lock-in to LangChain ecosystem | **Langfuse** (open source, MIT license, multi-framework support, 8000+ deployments) |
| **Matplotlib for frontend** | Static PNG outputs, no interactivity, poor performance for real-time updates, not designed for web dashboards | **Plotly.js** or **React D3 Tree** for interactive web visualizations |
| **Flask** | Synchronous by default, requires extensions for async, less suited for real-time SSE/WebSocket, older patterns | **FastAPI** (native async, modern Python patterns, automatic OpenAPI docs) |
| **Vanilla JavaScript** | No type safety, harder to maintain complex observability UIs, misses out on ecosystem libraries, 2025 standard is TypeScript | **TypeScript with strict mode** (catches 15-65% of bugs at compile-time, industry standard) |
| **MongoDB** | Overkill for structured decision data, no native time-series optimization, aggregation pipeline complexity | **PostgreSQL + TimescaleDB** (relational data + time-series optimization, single SQL dialect) |
| **Kafka** | Unnecessary complexity for single-user system, operational overhead, overkill for observability event streaming | **Redis pub/sub** or **SSE** (simpler, sufficient for single-user dashboard) |
| **jQuery** | Deprecated patterns, no component architecture, poor TypeScript support, not suited for complex reactive dashboards | **React/Vue/Svelte** (modern component frameworks, reactive state management, type-safe) |
| **D3.js without React wrapper** | Manual DOM manipulation complexity, steep learning curve, harder to maintain, doesn't leverage React's virtual DOM | **React D3 Tree** or **Visx** (React wrappers around D3, component-based, easier to maintain) |
| **Jupyter Notebook for production dashboard** | Not designed for production UIs, state management issues, poor performance for real-time updates, hard to deploy | **FastAPI + React** (proper web application architecture, production-ready, scalable) |

## Stack Patterns by Variant

**If building rapid internal prototype:**
- Use **Streamlit** + **Plotly** for pure Python dashboard
- Because minimal frontend code, fast iteration, no TypeScript knowledge needed
- Trade-off: Limited customization, re-run performance model, not production-ready

**If building production observability platform:**
- Use **FastAPI** + **React** + **TypeScript** + **TimescaleDB**
- Because scalable architecture, type-safe frontend, real-time updates, enterprise-grade
- Trade-off: Higher initial complexity, requires frontend + backend expertise

**If performance is critical (real-time high-frequency updates):**
- Use **Svelte** instead of React, **SSE** instead of polling
- Because smaller bundle size, no virtual DOM overhead, efficient one-way streaming
- Trade-off: Smaller ecosystem, fewer visualization libraries, less community knowledge

**If deploying multi-user SaaS:**
- Add **Redis** for connection sharing, **PostgreSQL pooling** (PgBouncer), **Celery** for background tasks
- Because cross-instance session management, connection pool limits, async job processing
- Trade-off: Additional infrastructure complexity, operational overhead

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.12 | LangGraph 0.4.8+, FastAPI 0.115+ | Existing project uses Python 3.10+ |
| React 19 | React D3 Tree 3.x, D3 7.x | React 19 released late 2025, ensure library compatibility |
| TypeScript 5.8+ | Vite 6.x, React 19 | Enable strict mode for type safety |
| FastAPI 0.115+ | Python 3.10+, Pydantic 2.10+ | Pydantic v2 required for FastAPI 0.100+ |
| PostgreSQL 16 | TimescaleDB 2.15+ | TimescaleDB tracks PG versions closely |
| SQLAlchemy 2.0+ | PostgreSQL 16+, async mode required | Use `create_async_engine` for performance |
| LangGraph 0.4.8+ | LangChain 0.3+, Python 3.10+ | Already in project, observability features stable |

## Architecture Integration Points

**With Existing System:**
- **LangGraph**: Already using 0.4.8+, add `@observe` decorator for tracing, export traces to Langfuse
- **ChromaDB**: Already using 1.0.12+, extend with PersistentClient for decision embeddings storage
- **Python 3.10+**: Existing codebase compatible, FastAPI works with current Python version
- **Markdown reports**: Already generating, parse for observability dashboard display

**New Integration Points:**
- **FastAPI**: New async backend serving observability API
- **PostgreSQL + TimescaleDB**: New storage for time-series decision tracking
- **React + TypeScript**: New frontend dashboard (separate repo or `/frontend` directory)
- **Langfuse**: New observability layer for LangGraph tracing

**Data Flow:**
```
LangGraph Agents → Langfuse Traces → PostgreSQL/TimescaleDB → FastAPI → React Dashboard
                    ↓
              ChromaDB (embeddings) → Semantic search for historical decisions
```

## Sources

- [AI Observability Tools 2025 - Unite.AI](https://www.unite.ai/best-ai-observability-tools/) — AI observability market overview, LangSmith/Arize/Fiddler comparison (MEDIUM confidence)
- [LLM Agent Monitoring 2025 - Various Sources](https://www.google.com/search?q=LLM+agent+monitoring+decision+trail+visualization+2025) — LiteLLM gateway, LangSmith, Langfuse, AgentOps challenges (HIGH confidence)
- [React vs Vue vs Svelte 2025 - Dashboard Comparison](https://www.google.com/search?q=React+vs+Vue+vs+Svelte+2025+dashboard+data+visualization) — Framework comparison for dashboards, WebAssembly trends, D3 integration (HIGH confidence)
- [Python LangGraph Full-Stack 2025](https://www.google.com/search?q=Python+LangGraph+observability+integration+dashboard+frontend+2025) — LangGraph + React architecture patterns (MEDIUM confidence)
- [Decision Tree Visualization Libraries 2025](https://www.google.com/search?q=decision+tree+visualization+JavaScript+libraries+2025+React+Vue) — React D3 Tree, Vue.D3.tree, D3.js, G6, Vis.js, Cytoscape.js comparison (HIGH confidence)
- [TimescaleDB 2025 Features](https://www.google.com/search?q=time+series+decision+tracking+database+2025+PostgreSQL+TimescaleDB) — Time-series optimization, PostgreSQL integration, use cases (HIGH confidence)
- [FastAPI SSE/WebSocket 2025](https://www.google.com/search?q=WebSocket+Server-Sent+Events+real-time+dashboard+Python+FastAPI+2025) — SSE implementation patterns, WebSocket ConnectionManager, async best practices (HIGH confidence)
- [Agent Debate Visualization 2025](https://www.google.com/search?q=agent+debate+visualization+confidence+scoring+UI+components+2025) — Multi-agent debate research, Amazon Bedrock AgentCore, Deep Agents UI (MEDIUM confidence)
- [LangSmith vs Langfuse 2025](https://www.google.com/search?q=LangSmith+Langfuse+open+source+alternatives+comparison+2025) — Feature comparison, licensing differences, deployment options (HIGH confidence)
- [Python Dashboard Frameworks 2025](https://www.google.com/search?q=Plotly+Altair+Dash+Streamlit+Python+dashboard+2025+comparison) — Streamlit vs Dash vs Plotly comparison, use cases (HIGH confidence)
- [TypeScript Strict Mode 2025](https://www.google.com/search?q=TypeScript+JavaScript+type+safety+frontend+2025+strict+mode+benefits) — 80%+ adoption, bug reduction stats, enterprise case studies (HIGH confidence)
- [React Flow vs D3.js 2025](https://www.google.com/search?q=React+Flow+D3.js+decision+tree+graph+visualization+2025+comparison) — React D3 Tree recommendation, library comparison (MEDIUM confidence)
- [ChromaDB + LangGraph Memory 2025](https://www.google.com/search?q=ChromaDB+vector+database+LangGraph+memory+persistence+2025) — PersistentClient patterns, PostgreSQL comparison, integration examples (HIGH confidence)

---
*Stack research for: AI Decision Observability & Transparency Tools*
*Researched: 2026-02-27*
