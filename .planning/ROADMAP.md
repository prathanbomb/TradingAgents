# Roadmap: Trading Agents Observatory

## Milestones

- ✅ **v1.0 Observatory Core** — Phases 1-4 (shipped 2026-02-28)
- 🚧 **v1.1 Performance Tracking** — Phase 5 (planned)

## Phases

<details>
<summary>✅ v1.0 Observatory Core (Phases 1-4) — SHIPPED 2026-02-28</summary>

- [x] Phase 1: Data Collection & Instrumentation (4/4 plans) — completed 2026-02-27
- [x] Phase 2: Confidence & Uncertainty (4/4 plans) — completed 2026-02-27
- [x] Phase 3: Decision Trail (4/4 plans) — completed 2026-02-27
- [x] Phase 4: Debate Explorer (4/4 plans) — completed 2026-02-28

</details>

### 🚧 v1.1 Performance Tracking (Planned)

- [ ] **Phase 5: Historical Performance** - Outcome correlation and agent-level performance attribution

## Phase Details

### Phase 5: Historical Performance

**Goal**: System correlates past decisions with actual market outcomes, enabling users to assess agent-level and system-level performance over time.

**Depends on**: Phase 1, Phase 2

**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04, PERF-05

**Success Criteria** (what must be TRUE):
1. System stores all decisions with full context for later retrieval
2. User can view past decisions and their outcomes
3. System correlates decisions with actual market outcomes after time delay
4. User can view agent-level performance attribution (which agents were right/wrong)
5. Performance metrics include confidence-weighted accuracy

**Plans**: 5 plans (TBD)

Plans:
- [ ] 05-01: Build OutcomeCorrelator to match decisions to market price data
- [ ] 05-02: Implement performance metrics calculation (win rate, P&L attribution, Sharpe ratio)
- [ ] 05-03: Create agent-level performance attribution and comparison
- [ ] 05-04: Build historical performance dashboard UI
- [ ] 05-05: Implement confidence-weighted accuracy tracking

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Collection | v1.0 | 4/4 | Complete | 2026-02-27 |
| 2. Confidence | v1.0 | 4/4 | Complete | 2026-02-27 |
| 3. Decision Trail | v1.0 | 4/4 | Complete | 2026-02-27 |
| 4. Debate Explorer | v1.0 | 4/4 | Complete | 2026-02-28 |
| 5. Historical Performance | v1.1 | 0/5 | Not started | - |
