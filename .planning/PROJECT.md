# Trading Agents Observatory

## What This Is

A transparency layer for the multi-agent LLM trading system that makes AI decisions visible, traceable, and trustworthy. Users can explore the full reasoning chain from raw data through analyst reports, debates, and final decisions - enabling informed judgment about whether to act on recommendations.

## Core Value

**Trust through visibility.** Users must understand WHY the system recommends what it does before they'll act on it.

## Requirements

### Validated

- ✓ Multi-agent trading analysis pipeline — existing (LangGraph orchestration with analysts, researchers, debaters, managers, traders)
- ✓ Data retrieval with vendor abstraction — existing (yfinance, Alpha Vantage, etc.)
- ✓ Agent memory and reflection system — existing (ChromaDB-backed)
- ✓ Report storage with multiple backends — existing (local, Cloudflare R2)
- ✓ Portfolio management integration — existing (Google Sheets)
- ✓ Decision tracking and performance storage — existing (backtracking module)
- ✓ Decision trail visualization — v1.0 (Timeline and causal chain from data → analysis → debate → decision)
- ✓ Agent debate explorer — v1.0 (Bull/bear arguments, risk debates, progressive disclosure)
- ✓ Confidence scoring — v1.0 (Multi-method extraction, aggregation, calibration tracking)
- ✓ Historical performance tracking — v1.0 (Decision-outcome correlation framework)

### Active

- [ ] Unified observability interface — single place to explore all observability features
- [ ] Historical outcome correlation — match past decisions to actual market outcomes

### Out of Scope

- Real-time trading execution — this is about understanding, not automating trades
- Mobile app — web-first interface
- Multi-user/accounts — single user system
- External API for observability data — internal use only

## Context

**Shipped v1.0:** 18,133 lines of Python across 24 files.
Tech stack: Python, LangChain/LangGraph, Pydantic, SQLite, GPT-3.5-turbo.

**Milestone Stats:**
- 4 phases, 16 plans, 106 commits
- Timeline: 62 days (Dec 28 → Feb 28)
- Integration: 93% cross-phase wiring (14/15 connections)

**Architecture:**
- `tradingagents.observability.instrumentation` — Data collection (DecisionRecord, AgentEvent, LanggraphCollector)
- `tradingagents.observability.confidence` — Confidence scoring (ConfidenceScorer, ConfidenceAggregator, CalibrationTracker)
- `tradingagents.observability.trail` — Decision trails (TrailBuilder, TrailQuery, TrailRenderer)
- `tradingagents.observability.debate` — Debate exploration (DebateParser, DebateSummarizer, DebateExplorer, JudgmentVisualizer)

**Known Tech Debt:**
- DebateSummary could show speaker confidence levels (enhancement)
- No unified API returning both DecisionTrail and DebateSummary for run_id (nice-to-have)

## Constraints

- **Tech Stack:** Python, LangChain/LangGraph, existing storage backends
- **Integration:** Must work with existing agent pipeline without disrupting analysis flow
- **Performance:** Observability layer should not significantly slow down analysis

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Focus on visibility over accuracy | User needs to trust system before improving it | ✓ Good — shipped decision trail, debate explorer |
| Build on existing backtracking module | Already tracks decisions, extend rather than replace | ✓ Good — DecisionRecord extends existing patterns |
| Non-blocking data collection | Observability must not slow trading pipeline | ✓ Good — async producer-consumer queue |
| Multi-method confidence extraction | Different agents express confidence differently | ✓ Good — verbalized, ensemble, token methods |
| LLM-based debate summarization | Full transcripts overwhelm users | ✓ Good — GPT-3.5-turbo with extractive fallback |
| Progressive disclosure pattern | Information density management | ✓ Good — 3-level disclosure (summary → key points → transcript) |

---
*Last updated: 2026-02-28 after v1.0 milestone*
