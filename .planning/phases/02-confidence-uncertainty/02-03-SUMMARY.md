---
phase: 02-confidence-uncertainty
plan: 03
title: "Confidence Calibration Tracking"
one_liner: "ECE-based calibration tracking with scikit-learn and SQLite persistence"
status: complete
completed_date: "2026-02-27"
duration_minutes: 2
---

# Phase 02 Plan 03: Confidence Calibration Tracking Summary

## Overview

Implemented confidence calibration tracking that records whether confidence levels match actual accuracy over time (CONF-03). The system now uses Expected Calibration Error (ECE) as the primary metric for assessing calibration quality, with SQLite storage for persistence and per-agent tracking capabilities.

**Key Achievement:** The system can now self-assess the reliability of its confidence scores, ensuring that an "80% confident" prediction is actually correct approximately 80% of the time.

## Implementation Details

### Files Created

1. **tradingagents/observability/confidence/calibration.py** (336 lines)
   - `CalibrationTracker` class for tracking confidence-outcome pairs
   - `CalibrationMetrics` dataclass with ECE, Brier score, sample count, and bin data
   - `calculate_ece()` helper function for standalone ECE computation
   - Edge case handling: empty data, insufficient samples, identical confidences
   - Uses scikit-learn's `calibration_curve` and `brier_score_loss` for accurate metrics

### Files Modified

1. **tradingagents/observability/storage/sqlite_backend.py** (+201 lines)
   - Added `calibration_outcomes` table with foreign key to `decision_records`
   - Added indexes: `idx_calibration_agent`, `idx_calibration_decision`, `idx_calibration_correct`
   - New methods:
     - `record_calibration_outcome()` - Store confidence-outcome pairs
     - `get_calibration_outcomes()` - Query with optional filters (agent, date range)
     - `get_calibration_metrics()` - Return CalibrationMetrics from stored data
     - `get_per_agent_calibration()` - Compute calibration per agent

2. **tradingagents/observability/confidence/__init__.py** (+96 lines)
   - Exported calibration components: `CalibrationTracker`, `CalibrationMetrics`, `calculate_ece`
   - Added `create_calibration_tracker()` factory function
   - Added `compute_system_calibration()` for DecisionRecord list processing
   - Added `assess_calibration_health()` for UI status display

## Database Schema

### calibration_outcomes Table

```sql
CREATE TABLE calibration_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    confidence REAL NOT NULL,
    was_correct BOOLEAN NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES decision_records(decision_id)
);

-- Indexes for efficient queries
CREATE INDEX idx_calibration_agent ON calibration_outcomes(agent_name, recorded_at);
CREATE INDEX idx_calibration_decision ON calibration_outcomes(decision_id);
CREATE INDEX idx_calibration_correct ON calibration_outcomes(was_correct);
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed get_per_agent_calibration() parameter mismatch**
- **Found during:** Task 2 verification
- **Issue:** `get_per_agent_calibration()` passed `limit` parameter to `get_calibration_metrics()`, which doesn't accept it
- **Fix:** Removed `limit` parameter from `get_per_agent_calibration()` signature
- **Files modified:** `tradingagents/observability/storage/sqlite_backend.py`
- **Commit:** N/A (fixed in same commit as Task 2)

**2. [Rule 3 - Blocking] Missing scikit-learn dependency**
- **Found during:** Task 1 verification
- **Issue:** scikit-learn not installed in system Python environment
- **Fix:** Installed scikit-learn using `pip3 install scikit-learn`
- **Impact:** Required for ECE calculation using sklearn.calibration.calibration_curve

## Technical Decisions

### D02-03-01: Use scikit-learn for ECE calculation instead of manual implementation
- **Rationale:** Well-tested library handles edge cases (empty bins, boundary conditions) correctly; avoids common statistical errors
- **Impact:** ECE calculations are numerically stable and match industry standards

### D02-03-02: Store calibration data in separate table vs. embedding in decision_records
- **Rationale:** Enables efficient calibration queries without scanning decision_records; supports per-agent analysis without filtering
- **Impact:** Calibration queries are O(log n) with indexes vs. O(n) table scans

### D02-03-03: Calibration threshold set to 0.1 for "well calibrated" status
- **Rationale:** Industry standard from machine learning calibration research; balances strictness with practical usability
- **Impact:** Systems with ECE < 0.1 are considered reliable for user decisions

## Commits

| Task | Commit | Message | Files |
|------|--------|---------|-------|
| 1 | 2d96031 | feat(02-03): implement CalibrationTracker with ECE calculation | calibration.py |
| 2 | b8aa6f2 | feat(02-03): extend SQLite backend with calibration storage | sqlite_backend.py |
| 3 | 439d110 | feat(02-03): create calibration integration helpers | confidence/__init__.py |

**Total:** 3 commits, 3 files created/modified, 633 lines added

## Verification Results

### ECE Calculation Test
- Well-calibrated data (80% conf → 80% accuracy): **ECE = 0.0000** ✓
- Proper handling of edge cases: empty data, insufficient samples, identical confidences ✓

### SQLite Storage Test
- Calibration outcomes persisted correctly ✓
- Query with agent name filter working ✓
- Foreign key relationship to decision_records enforced ✓

### Metrics Retrieval Test
- get_calibration_metrics() returns CalibrationMetrics with all fields ✓
- ECE, Brier score, sample count computed correctly ✓
- is_well_calibrated flag accurate (ECE < 0.1) ✓

### Per-Agent Calibration Test
- get_per_agent_calibration() returns dict of {agent_name: CalibrationMetrics} ✓
- Each agent tracked separately ✓
- Handles agents with different sample counts ✓

## Calibration Accuracy

### Test Data Results
- **Well-calibrated data:** ECE = 0.0000 (perfectly calibrated)
- **Sample count:** 200 outcomes
- **Brier score:** 0.1850 (lower is better)
- **Status:** Well calibrated ✓

### Edge Cases Handled
- Empty data → Returns metrics with sample_count=0, is_well_calibrated=False
- Fewer than n_bins samples → Returns ECE=0.0 with warning logged
- All identical confidences → Returns ECE=0.0 with debug logged

## Next Steps

### Plan 04: Confidence History Query Interface
- Build query interface for confidence history with trend analysis
- Add calibration summary endpoints for dashboard display
- Implement confidence trend visualization data preparation

### Phase 5: Performance Correlation
- Record calibration outcomes when decision outcomes are calculated
- Link confidence scores to actual returns
- Analyze whether confidence predicts profitability

### Phase 4: Visualization (Future)
- Generate reliability diagrams from bin_data
- Plot calibration curves over time
- Show per-agent calibration comparison charts

## Requirements Satisfied

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| CONF-03 | Confidence calibration tracking | Complete | CalibrationTracker records outcomes, computes ECE, stores in SQLite |
| CONF-03 | ECE calculation using scikit-learn | Complete | Uses sklearn.calibration.calibration_curve |
| CONF-03 | Per-agent calibration metrics | Complete | get_per_agent_calibration() returns metrics per agent |
| CONF-03 | Calibration data persistence | Complete | SQLite calibration_outcomes table with indexes |

## Integration Points

### Existing Components Used
- **DecisionRecord.model** - Provides confidence field for calibration tracking
- **SQLiteDecisionStore** - Extended with calibration storage methods
- **Phase 1 infrastructure** - Builds on decision_records table with foreign key

### Future Integrations
- **Phase 4 (Visualization)** - CalibrationMetrics.bin_data for reliability diagrams
- **Phase 5 (Performance Correlation)** - DecisionRecord.calculate_outcome() triggers calibration recording
- **Dashboard UI** - assess_calibration_health() for status display

## Dependencies Installed

- scikit-learn 1.8.0 (via pip3 install scikit-learn)
  - Required for: calibration_curve, brier_score_loss
  - Already installed: numpy, scipy, joblib, threadpoolctl (dependencies)

## Performance Notes

- ECE calculation: O(n) where n = number of samples
- Calibration queries: O(log n) with indexes on agent_name and recorded_at
- Storage overhead: ~100 bytes per calibration outcome
- Recommended: Archive old calibration data quarterly for large deployments

## Known Limitations

1. **Calibration requires outcome data** - Cannot assess calibration until Phase 5 (Performance Correlation) calculates actual returns
2. **Minimum samples for accuracy** - Need 10+ samples per agent for reliable ECE calculation
3. **No temperature scaling yet** - Post-hoc calibration (temperature scaling) deferred to future phase
4. **Static threshold** - Well-calibrated threshold (0.1) hardcoded; could be configurable

## Success Criteria Met

- [x] CalibrationTracker records confidence-outcome pairs
- [x] ECE calculation uses sklearn.calibration.calibration_curve correctly
- [x] SQLite backend stores and retrieves calibration data
- [x] get_calibration_metrics returns CalibrationMetrics with all fields
- [x] Per-agent calibration computed separately for each agent type
- [x] Well-calibrated threshold (ECE < 0.1) correctly assessed
- [x] Integration helpers make calibration easy to use
- [x] Module exports include all calibration components

## Files Summary

| File | Lines Created | Lines Modified | Purpose |
|------|---------------|----------------|---------|
| calibration.py | 336 | 0 | Core calibration tracking logic |
| sqlite_backend.py | 201 | 0 | Storage extension for calibration |
| confidence/__init__.py | 96 | 2 | Integration helpers and exports |
| **Total** | **633** | **2** | **Calibration infrastructure** |
