# Project Retrospective

Living document capturing lessons learned across milestones.

---

## Milestone: v1.0 — Trading Agents Observatory

**Shipped:** 2026-02-28
**Phases:** 4 | **Plans:** 16

### What Was Built

1. **Data Collection & Instrumentation** — Non-blocking async pipeline capturing agent events via LangGraph astream_events
2. **Confidence & Uncertainty** — Multi-method confidence extraction (verbalized, ensemble, token) with calibration tracking
3. **Decision Trail** — Timeline visualization with causal chain reconstruction from data → analysis → debate → decision
4. **Debate Explorer** — Bull/bear argument parsing with LLM-based summarization and progressive disclosure

### What Worked

- **Non-blocking architecture** — Producer-consumer queue with SQLite backend kept observability from slowing trading pipeline
- **Pydantic-first design** — Strong typing made integration between phases reliable
- **Progressive disclosure** — 3-level summarization (summary → key points → transcript) prevented information overload
- **Phase dependencies** — Clear wave structure with explicit depends_on made parallel execution safe

### What Was Inefficient

- **Manual traceability updates** — REQUIREMENTS.md traceability table required manual syncing with VERIFICATION.md results
- **Context window pressure** — Some plans hit 4-task upper boundary, causing context degradation warnings
- **No unified UI layer** — Each phase built its own renderer; could benefit from shared visualization framework

### Patterns Established

- **Async-first data collection** — All observability data flows through non-blocking queue
- **Pydantic models at boundaries** — Every phase defines input/output models for cross-phase communication
- **SQLite for queryability** — Structured data in SQLite enables complex queries without external dependencies
- **LLM with fallback** — GPT-3.5-turbo for quality, sumy for free extractive fallback when API unavailable

### Key Lessons

1. **Start with data model, end with visualization** — Phase 1 (models) → Phase 3/4 (renderers) worked well
2. **Confidence extraction is harder than expected** — Verbalized confidence unreliable; ensemble and token methods needed
3. **Progressive disclosure is essential** — Full LLM transcripts overwhelm users; summarization is not optional
4. **Cross-phase integration needs explicit wiring** — Integration checker caught a missing confidence → debate link

### Cost Observations

- Model mix: 60% sonnet, 40% haiku (no opus needed)
- Sessions: ~8 major execution sessions
- Notable: Phase 4 debate summarization cost ~$0.50/1000 debates with GPT-3.5-turbo

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 4 |
| Plans | 16 |
| Tasks | ~55 |
| LOC | 18,133 |
| Days | 62 |
| Commits | 106 |
| Integration Health | 93% |
| Requirements Verified | 100% |

---

*Last updated: 2026-02-28*
