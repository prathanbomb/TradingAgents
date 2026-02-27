---
phase: "04"
plan: "04-04"
title: "Debate Resolution and Judgment Visualization"
subsystem: "Debate Explorer"
tags: ["debate", "judgment", "visualization", "progressive-disclosure"]
requirements: ["DEBATE-03", "DEBATE-05", "DEBATE-06"]
depends_on:
  provides:
    - "JudgmentView - Structured judgment display with progressive disclosure"
    - "DecisionInfluence - Links judgment outcomes to trading decisions"
    - "JudgmentVisualizer - Extracts judgment reasoning and winning arguments"
    - "JudgmentRenderer - Text-based rendering with visual indicators"
  affects:
    - "Phase 5 (Performance) - Can correlate judgment quality with outcomes"
    - "Future UI layer - Consumes JudgmentRenderer for web interface"
  tech_stack:
    added:
      - "JudgmentView Pydantic model for progressive disclosure"
      - "DecisionInfluence Pydantic model for alignment tracking"
      - "JudgmentVisualizer for judgment analysis"
      - "JudgmentRenderer for text-based display"
    patterns:
      - "Progressive disclosure (3-level pattern consistent with DebateSummary)"
      - "Keyword matching for argument identification"
      - "Regex-based reasoning extraction"
      - "Emoji-based visual indicators"
key_files_created:
  - tradingagents/observability/debate/judgment.py
  - tradingagents/observability/debate/models.py (added JudgmentView, DecisionInfluence)
  - tradingagents/observability/debate/__init__.py (updated exports)
key_files_modified: []
decisions: []
metrics:
  duration_hours: 0.03
  completed_date: "2026-02-27T17:37:00Z"
---

# Phase 04 Plan 04-04: Debate Resolution and Judgment Visualization Summary

**One-liner:** Regex-based judgment visualization with progressive disclosure, keyword-based winning argument identification, and alignment tracking between judgment outcomes and trading decisions.

## Overview

Created `JudgmentVisualizer` and `JudgmentRenderer` to analyze how research managers and risk judges resolved debates, enabling users to understand which arguments prevailed and how debates influenced final trading decisions. Implemented 3-level progressive disclosure pattern consistent with existing debate infrastructure.

## Implementation Summary

### Task 1: Create JudgmentVisualizer for Resolution Display ✅
**Commit:** `dfe3ddf`

Created `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/judgment.py` with:

- **JudgmentVisualizer class:**
  - `visualize_judgment()` - Creates structured view with 3 disclosure levels
  - `extract_judgment_reasoning()` - Uses regex patterns to identify reasoning ("because", "due to", "given that")
  - `identify_winning_arguments()` - Keyword matching between judgment and argument content
  - `link_judgment_to_decision()` - Analyzes alignment between judgment and final_signal

- **Winner identification:**
  - Investment debates: Matches "bull"/"bear" keywords
  - Risk debates: Matches "risky"/"safe"/"neutral" keywords
  - Ambiguous judgments: Returns "Inconclusive" for "too close to call" patterns

- **Alignment scoring:**
  - Aligned (0.85): Bull wins + BUY, Bear wins + SELL
  - Opposed (0.15): Bull wins + SELL, Bear wins + BUY
  - Neutral (0.50): All other cases

### Task 2: Create JudgmentView and DecisionInfluence Models ✅
**Commit:** `aab9e11`

Added to `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/models.py`:

- **JudgmentView model:**
  - Level 1 (always shown): winner, winner_summary, judgment_summary (200 char max)
  - Level 2 (expandable): winning_arguments, losing_arguments, judgment_reasoning
  - Level 3 (expandable): full_judgment, all_arguments by speaker
  - Validators truncate summaries to 200 chars
  - `to_dict(exclude_level)` supports progressive disclosure

- **DecisionInfluence model:**
  - Tracks judgment_winner, final_decision, alignment, influence_score
  - `get_alignment_description()` for human-readable output
  - Supports 0.0-1.0 influence scoring

### Task 3: Implement JudgmentRenderer for Display ✅
**Commit:** `dfe3ddf` (included in Task 1)

Added to `judgment.py`:

- **JudgmentRenderer class:**
  - `render_judgment_view()` - 3-level disclosure rendering
  - `render_decision_influence()` - Shows alignment, influence score, reasoning
  - `render_judgment_timeline()` - Chronological arguments with winning marked (✓)

- **Visual formatting:**
  - Emojis: 🐂 Bull, 🐻 Bear, ⚠️ Risk, 🛡️ Safe, ⚖️ Neutral, ✅ aligned, ⚠️ opposed
  - Markdown-style headers, bullet points, separators
  - Level 1 fits in ~5 lines for quick scanning

### Task 4: Export JudgmentVisualizer and Related Classes ✅
**Commit:** `773bcff`

Updated `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/__init__.py`:

- Added JudgmentView, DecisionInfluence to model imports
- Added JudgmentVisualizer, JudgmentRenderer to component imports
- Updated module docstring with judgment visualization description
- Organized imports by source (models → parser → summarizer → explorer → judgment)

## Verification

### Functional Tests ✅
Created and executed comprehensive test suite:

1. **Visualize investment debate judgment** ✅
   - Input: Debate with "Bull case is stronger due to earnings momentum"
   - Output: Winner="Bull Analyst", winner_summary extracted correctly

2. **Visualize risk debate judgment** ✅
   - Tested with risky/safe/neutral speaker patterns

3. **Identify winning arguments** ✅
   - Input: Bull arguments with "earnings", judgment with "earnings momentum"
   - Output: Bull arguments containing "earnings" keyword returned

4. **Link judgment to decision** ✅
   - Input: Bull wins, final_signal=BUY
   - Output: alignment="aligned", influence_score=0.85

5. **Render progressive disclosure levels** ✅
   - Level 1: Winner + summary only
   - Level 2: Winner + summary + key arguments
   - Level 3: Winner + summary + key arguments + full judgment

6. **Render judgment timeline with highlights** ✅
   - Winning arguments marked with ✓
   - Losing arguments unmarked

### Edge Cases ✅
1. **Ambiguous judgment** ✅
   - Input: "Too close to call, data is mixed"
   - Output: winner="Inconclusive", winner_summary="No clear winner"

2. **Missing judgment** ✅
   - Input: Judgment with empty decision field
   - Output: winner="Unknown", logs warning

3. **Judgment-decision mismatch** ✅
   - Input: Bull wins, final_signal=SELL
   - Output: alignment="opposed", influence_score=0.15

## Deviations from Plan

### Auto-fixed Issues

**None - plan executed exactly as written.**

All tasks completed according to specification:
- Task 1: JudgmentVisualizer implemented with all required methods
- Task 2: Models added to models.py with proper validators
- Task 3: JudgmentRenderer included in same file as JudgmentVisualizer (optimized implementation)
- Task 4: Exports updated in __init__.py

## Technical Notes

### Design Decisions

1. **Keyword matching for argument identification (D04-04-01)**
   - Rationale: LLM-based argument identification is expensive, keyword overlap works for structured debates
   - Tradeoff: Less accurate than LLM analysis, but adequate for current use case

2. **Text-based rendering for Phase 4 (D04-03-01)**
   - Rationale: Progressive disclosure pattern can be established with text, portable to web UI later
   - Impact: Core functionality works immediately, no framework dependency

3. **Influence scoring binary alignment**
   - Current: Simple alignment check (winner matches decision → 0.85)
   - Future: Could weight by judgment confidence and argument strength

### Known Limitations

- **Argument matching is approximate:** Keyword overlap is a crude proxy for "what the judge found persuasive"
- **Ambiguous judgments common:** "Too close to call" or "mixed signals" preserved rather than forced into binary winner
- **Influence score is simple:** Current calculation is binary, could be enhanced with confidence weighting

## Requirements Coverage

| Requirement | Coverage | Evidence |
|------------|----------|----------|
| DEBATE-03: Users can see how judge resolved debates | ✅ Complete | JudgmentView with winner identification and reasoning |
| DEBATE-05: Extract key arguments, not full transcripts | ✅ Complete | identify_winning_arguments() returns top arguments |
| DEBATE-06: Progressive disclosure | ✅ Complete | 3-level pattern in JudgmentView (summary → key arguments → full) |

## Phase 4 Completion

This plan completes **Phase 4: Debate Explorer**. All requirements satisfied:

1. **DEBATE-01, DEBATE-02:** Explore bull/bear arguments (04-01, 04-03) ✅
2. **DEBATE-03:** See how judge resolved debates (04-04) ✅
3. **DEBATE-04:** Explore risk analyst debates (04-01, 04-03) ✅
4. **DEBATE-05:** Key arguments, not full transcripts (04-02, 04-04) ✅
5. **DEBATE-06:** Progressive disclosure (04-02, 04-03, 04-04) ✅

### Integration Points

- **Phase 1:** DecisionRecord.debate_state provides raw debate data
- **Phase 2:** Confidence tracking can be added to judgment confidence field
- **Phase 3:** DecisionTrail links debates to decisions via run_id
- **Phase 5:** DecisionInfluence enables performance correlation

### Next Phase Readiness

- All debate data structured and queryable
- Judgment-decision linkage enables performance correlation
- Progressive disclosure patterns established for UI layer
- Ready for Phase 5 (Performance Correlation)

## Self-Check: PASSED

**Files Created:**
- ✅ `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/judgment.py`
- ✅ `/Users/prathanbomb/Documents/workspace-python/trading-agents/.planning/phases/04-debate-explorer/04-04-SUMMARY.md`

**Files Modified:**
- ✅ `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/models.py`
- ✅ `/Users/prathanbomb/Documents/workspace-python/trading-agents/tradingagents/observability/debate/__init__.py`

**Commits Verified:**
- ✅ `dfe3ddf`: feat(04-04): create JudgmentVisualizer and JudgmentRenderer classes
- ✅ `aab9e11`: feat(04-04): add JudgmentView and DecisionInfluence models to models.py
- ✅ `773bcff`: feat(04-04): export JudgmentVisualizer and JudgmentRenderer from debate module

**Tests Passed:**
- ✅ All functional tests passed (judgment visualization, alignment, edge cases)
