# Phase 4: Debate Explorer - Quick Reference

**Status:** Plans created, ready for execution
**Created:** 2026-02-28

## Quick Start

```bash
# Execute Phase 4
/gsd:execute-phase 04-debate-explorer
```

## Plans Overview

| Plan | Wave | Description | Tasks | Requirements |
|------|------|-------------|-------|--------------|
| 04-01 | 1 | Build DebateParser | 3 | DEBATE-01, DEBATE-02, DEBATE-04 |
| 04-02 | 2 | Argument summarization | 4 | DEBATE-05, DEBATE-06 |
| 04-03 | 3 | DebateExplorer interface | 4 | DEBATE-01, DEBATE-02, DEBATE-04, DEBATE-06 |
| 04-04 | 3 | Judgment visualization | 4 | DEBATE-03, DEBATE-05, DEBATE-06 |

## Key Components

### Data Models (`models.py`)
- `Argument`: Single argument from a speaker
- `Judgment`: Judge's decision on the debate
- `Debate`: Complete debate with all arguments
- `DebateSummary`: Progressive disclosure model (3 levels)
- `JudgmentView`: Structured resolution view
- `DecisionInfluence`: Debate-decision linkage

### Core Classes
- `DebateParser`: Extract structured debates from `DecisionRecord.debate_state`
- `DebateSummarizer`: LLM-based key point extraction (GPT-3.5-turbo)
- `DebateExplorer`: Query and filter debates by ticker, date, type
- `DebateRenderer`: Text-based progressive disclosure rendering
- `JudgmentVisualizer`: Extract and display judgment reasoning
- `JudgmentRenderer`: Render judgment with winning arguments

## File Structure

```
tradingagents/observability/debate/
├── __init__.py          # Module exports
├── models.py            # Pydantic models (Argument, Judgment, Debate, etc.)
├── parser.py            # DebateParser for extracting structured debates
├── summarizer.py        # DebateSummarizer for key point extraction
├── explorer.py          # DebateExplorer, DebateRenderer
└── judgment.py          # JudgmentVisualizer, JudgmentRenderer
```

## Dependencies

**Required (complete):**
- Phase 1: `DecisionRecord.debate_state` ✅
- Phase 3: `DecisionTrail.run_id` ✅
- `langchain-openai` (already installed)

**Optional (for 04-02):**
- `sumy` (extractive summarization fallback)

## Execution Notes

**Wave 1 (04-01):** Autonomous, no human review needed
- Creates debate data models
- Implements regex-based speaker identification
- Handles both investment (2 speakers) and risk (3 speakers) debates

**Wave 2 (04-02):** **Requires human review** (LLM costs)
- Uses GPT-3.5-turbo for summarization (~$0.004 per debate)
- Implements caching to control costs
- Falls back to extractive summarization if LLM unavailable
- **Monitor API costs during execution**

**Wave 3 (04-03, 04-04):** Autonomous, can run in parallel
- `04-03`: Query interface and text-based rendering
- `04-04`: Judgment visualization and decision linkage

## Success Criteria

Phase 4 is complete when:
1. ✅ Users can explore bull researcher arguments (04-01, 04-03)
2. ✅ Users can explore bear researcher arguments (04-01, 04-03)
3. ✅ Users can see how research manager judged the debate (04-04)
4. ✅ Users can explore risk analyst debates (04-01, 04-03)
5. ✅ System extracts key arguments, not full transcripts (04-02, 04-04)
6. ✅ Progressive disclosure (summary → key points → transcript) (04-02, 04-03, 04-04)

## Risk Mitigation

| Risk | Plan | Mitigation |
|------|------|------------|
| LLM costs exceed budget | 04-02 | Use GPT-3.5-turbo, cache summaries, monitor costs |
| Regex parsing fails | 04-01 | Graceful degradation, log warnings |
| Full transcripts overwhelm users | 04-02 | Progressive disclosure (3 levels) |
| Ambiguous judgments | 04-04 | Mark as "Inconclusive", preserve original text |
| SQLite JSON slow | 04-03 | Limit results (default 100), defer FTS5 |

## Integration Points

**Data flow:**
```
DecisionRecord.debate_state (Phase 1)
    ↓
DebateParser → Debate (04-01)
    ↓
DebateSummarizer → DebateSummary (04-02)
    ↓
DebateExplorer → Query & Filter (04-03)
    ↓
JudgmentVisualizer → JudgmentView (04-04)
```

**Linkages:**
- `run_id` links debates to `DecisionTrail` (Phase 3)
- `final_signal` links judgments to trading decisions
- `DecisionRecord` provides source data for parsing

## Next Phase Handoff

**Phase 5 (Historical Performance) will receive:**
- Structured debate data for quality-outcome correlation
- `DecisionInfluence` for measuring debate impact
- Judgment-decision linkage for performance attribution

## Files to Read

- `.planning/phases/04-debate-explorer/04-SUMMARY.md` - Complete planning summary
- `.planning/phases/04-debate-explorer/04-RESEARCH.md` - Technical research
- `.planning/phases/04-debate-explorer/04-*-PLAN.md` - Individual plans

## Commands

```bash
# View plans
ls .planning/phases/04-debate-explorer/*-PLAN.md

# Execute phase
/gsd:execute-phase 04-debate-explorer

# Check status after execution
cat .planning/STATE.md
```
