# Phase 4: Debate Explorer - Planning Summary

**Planned:** 2026-02-28
**Status:** Plans created, ready for execution
**Plans:** 4

## Overview

Phase 4 implements the Debate Explorer feature, enabling users to explore agent arguments (bull/bear research debates and risk analyst debates) with progressive disclosure from summary to detailed transcripts. This phase builds on Phase 1's data collection (`DecisionRecord.debate_state`) and Phase 3's `DecisionTrail` infrastructure to provide structured access to the reasoning process behind trading decisions.

## Requirements Coverage

| Requirement | Description | Plans Covering |
|-------------|-------------|----------------|
| DEBATE-01 | Users can explore bull researcher arguments for each decision | 04-01, 04-03 |
| DEBATE-02 | Users can explore bear researcher arguments for each decision | 04-01, 04-03 |
| DEBATE-03 | Users can see how the research manager judged the debate | 04-04 |
| DEBATE-04 | Users can explore risk analyst debates (risk/safe/neutral perspectives) | 04-01, 04-03 |
| DEBATE-05 | System extracts and highlights key arguments rather than showing full transcripts | 04-02, 04-04 |
| DEBATE-06 | Progressive disclosure shows summary first, details on demand | 04-02, 04-03, 04-04 |

**Coverage:** 6/6 requirements (100%)

## Plans Created

### Wave 1: Foundation (Independent)
- **04-01-PLAN.md**: Build DebateParser to extract and structure debate arguments
  - Creates `Debate`, `Argument`, `Judgment` Pydantic models
  - Implements regex-based speaker identification for bull/bear/risk debates
  - Handles both `InvestDebateState` (2 speakers) and `RiskDebateState` (3 speakers)
  - **Requirements:** DEBATE-01, DEBATE-02, DEBATE-04
  - **Autonomous:** Yes

### Wave 2: Summarization (Depends on 04-01)
- **04-02-PLAN.md**: Implement argument summarization and key point extraction
  - Creates `DebateSummarizer` with LLM-based key point extraction
  - Implements 3-level progressive disclosure: summary → key points → full transcript
  - Uses GPT-3.5-turbo for cost efficiency with extractive fallback (sumy)
  - Caches summaries to control LLM API costs
  - **Requirements:** DEBATE-05, DEBATE-06
  - **Autonomous:** No (requires LLM API key validation and cost monitoring)

### Wave 3: Query and Visualization (Depends on 04-01, 04-02)
- **04-03-PLAN.md**: Create DebateExplorer interface for querying and filtering debates
  - Creates `DebateExplorer` for querying debates by ticker, date, type
  - Extends `SQLiteDecisionStore` with debate query methods
  - Implements `DebateRenderer` for progressive disclosure display
  - Links debates to `DecisionTrail` via `run_id`
  - **Requirements:** DEBATE-01, DEBATE-02, DEBATE-04, DEBATE-06
  - **Autonomous:** Yes

- **04-04-PLAN.md**: Build debate resolution and judgment visualization
  - Creates `JudgmentVisualizer` to extract and display judgment reasoning
  - Identifies winning arguments from judgment text
  - Links judgments to final trading decisions via `DecisionInfluence`
  - Implements `JudgmentRenderer` for progressive disclosure
  - **Requirements:** DEBATE-03, DEBATE-05, DEBATE-06
  - **Autonomous:** Yes

## Wave Structure

```
Wave 1 (04-01): Foundation
    ↓
Wave 2 (04-02): Summarization
    ↓
Wave 3 (04-03, 04-04): Query and Visualization (parallel)
```

## Dependencies

- **Phase 1** (Data Collection): `DecisionRecord.debate_state` ✅ Complete
- **Phase 3** (Decision Trail): `DecisionTrail.run_id` for linking ✅ Complete
- **External**: `langchain-openai` for LLM access (already installed)

## Key Design Decisions

### D04-01-01: Regex-based speaker identification
- **Rationale:** Debate format is structured ("Speaker: text"), regex is faster and sufficient
- **Impact:** Fast parsing, no LLM dependency for argument extraction
- **Tradeoff:** Less flexible than spaCy NER, but debates follow consistent format

### D04-02-01: GPT-3.5-turbo for summarization
- **Rationale:** Cost efficiency ($0.002/1K tokens vs GPT-4's $0.03/1K tokens)
- **Impact:** ~$0.004 per 10-turn debate, acceptable for single-user system
- **Tradeoff:** Lower quality than GPT-4, but sufficient for trading debate summarization

### D04-02-02: Permanent summary caching
- **Rationale:** Debates are immutable after storage, no need to re-summarize
- **Impact:** One LLM call per debate, stored in SQLite alongside `DecisionRecord`
- **Tradeoff:** Storage overhead vs API cost savings (API savings dominate)

### D04-03-01: Text-based rendering for Phase 4
- **Rationale:** Web UI deferred to future phase, text rendering sufficient for v1
- **Impact:** Progressive disclosure pattern established, portable to web UI
- **Tradeoff:** Limited interactivity (no expandable accordions), but core functionality works

### D04-04-01: Keyword matching for winning arguments
- **Rationale:** LLM-based argument identification is expensive, keyword overlap works for structured debates
- **Impact:** Fast, no additional API costs
- **Tradeoff:** Less accurate than LLM analysis, but highlights relevant arguments

## Integration Points

### Data Flow
```
Phase 1: DecisionRecord.debate_state
    ↓
Plan 04-01: DebateParser → Debate (structured arguments)
    ↓
Plan 04-02: DebateSummarizer → DebateSummary (progressive disclosure)
    ↓
Plan 04-03: DebateExplorer → Query & Filter → DebateRenderer
    ↓
Plan 04-04: JudgmentVisualizer → JudgmentView → JudgmentRenderer
```

### Linkages
- **DecisionTrail (Phase 3):** `run_id` links debates to decisions
- **SQLite Storage (Phase 1):** Extended with debate query methods
- **Confidence (Phase 2):** Can be added to `Judgment.confidence` in future

## Success Criteria

Phase 4 is complete when:
1. ✅ Users can explore bull researcher arguments for each decision (04-01, 04-03)
2. ✅ Users can explore bear researcher arguments for each decision (04-01, 04-03)
3. ✅ Users can see how the research manager judged the debate (04-04)
4. ✅ Users can explore risk analyst debates (risk/safe/neutral) (04-01, 04-03)
5. ✅ System extracts and highlights key arguments rather than showing full transcripts (04-02, 04-04)
6. ✅ Progressive disclosure shows summary first, details on demand (04-02, 04-03, 04-04)

## Execution Readiness

**Plans created:** 4/4 (100%)
**Requirements mapped:** 6/6 (100%)
**Dependencies satisfied:** Phase 1 ✅, Phase 3 ✅
**Autonomous plans:** 3/4 (75%) - 04-02 requires human review for LLM costs

**Next steps:**
1. Execute `/gsd:execute-phase 04-debate-explorer` to start implementation
2. Monitor LLM API costs during 04-02 execution
3. Validate debate parsing on real `DecisionRecord` data from storage

## Files Modified

**New files:**
- `tradingagents/observability/debate/__init__.py`
- `tradingagents/observability/debate/models.py`
- `tradingagents/observability/debate/parser.py`
- `tradingagents/observability/debate/summarizer.py`
- `tradingagents/observability/debate/explorer.py`
- `tradingagents/observability/debate/judgment.py`

**Modified files:**
- `tradingagents/observability/storage/sqlite_backend.py` (add debate query methods)

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM summarization costs exceed budget | Use GPT-3.5-turbo, cache summaries, monitor costs in 04-02 |
| Regex parsing fails on malformed debates | Graceful degradation, log warnings, skip malformed records |
| Full transcript display overwhelms users | Progressive disclosure (3 levels), truncate in timeline view |
| Judgment extraction is ambiguous | Preserve original text, mark as "Inconclusive" if unclear |
| SQLite JSON queries are slow | Limit results (default 100), defer FTS5 optimization to Phase 5 |

## Handoff to Phase 5

**Phase 5 (Historical Performance) will receive:**
- Structured debate data for correlating debate quality with outcomes
- `DecisionInfluence` for measuring debate impact on trading decisions
- Judgment-decision linkage for performance attribution

**Phase 5 can leverage:**
- Debate winner → outcome correlation (did bull-biased debates perform better?)
- Argument quality metrics (did data-driven arguments correlate with accuracy?)
- Judgment confidence → calibration analysis (were confident judgments correct?)

---

**Planning completed:** 2026-02-28
**Plans ready for execution:** Yes
**Estimated execution time:** 2-4 hours (4 plans, ~30-60 min each)
