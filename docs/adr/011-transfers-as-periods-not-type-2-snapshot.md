# ADR 011: Transfers as Periods, Not Type 2 Snapshot

## Date
2026-05-22

## Status
Accepted

## Context
The platform needs reliable answers to "which club was this player at on
date D?" and related transfer analytics. Two different mechanisms exist in
the source data:

**Transfer events** — discrete moves with `transfer_date`, classified in
`int_transfers` (permanent, loan, free, fee-bearing, etc.). Stint boundaries
are defined by business logic: `period_start_date` = move in,
`period_end_date` = `lead(transfer_date)` per player in
`int_player_club_periods`.

**Squad snapshots** — `stg_team_squads` reflects the API's current roster on
each ingest (quarterly, weekly in transfer windows). Membership can change
on re-ingest without a corresponding transfer row.

An early design discussion included dbt **Type 2 snapshots** on transfers
(`dbt_valid_from` / `dbt_valid_to`) alongside `scd_player_club` and
`scd_club_league`. Market-value SCD was also considered but rejected
separately — `raw_players` has no `market_value` column; fees live in
`fact_player_market_value_period`.

## Decision
**Do not** build `scd_player_transfer` or snapshot `stg_transfers` /
`int_transfers`.

**Transfer history (analytics):**
- Keep `int_player_club_periods` in the intermediate layer (full refresh).
- Expose consumption via **`fact_player_club_period`** in `football_core`.
- Analysts and marts join `fact_player_club_period` — not `int_*`, not
  transfer snapshots.

**Squad and participation (audit / re-ingest):**
- Implement **`scd_player_club`** — dbt snapshot on `stg_team_squads`,
  `unique_key='player_id'`, `check_cols` include `team_id`.
- Implement **`scd_club_league`** — dbt snapshot on domestic
  `stg_team_seasons` (clubs + `league_type = 'league'`),
  `unique_key=['team_id', 'season_year']`, `check_cols` include `league_id`.
- Analytic participation spine remains **`int_club_league_periods`** (no
  `dbt_valid_*` columns).

**Execution:** snapshots run via `dbt snapshot --select scd_player_club
scd_club_league`, separate from `dbt run`.

## Alternatives Considered
**Type 2 snapshot on `int_transfers`** — would duplicate stint logic and
fight `lead()`-based `period_end_date` updates. Each new transfer ingested
must rewrite end dates on prior rows for the same player. That is period
semantics, not append-only SCD versioning. Rejected.

**Only `scd_player_club` for transfer history** — captures roster state at
ingest time but misses stint start dates from `transfer_date` and does not
include loans/frees that never appear in fee facts. Rejected as sole history
model.

**Type 2 snapshot on `dim_player`** (age, photo, nationality) — low analytic
value; Type 1 `dim_player` is sufficient. Rejected.

**`scd_player_market_value`** — no valuation field in API ingest. Fee strings
remain on `fact_player_market_value_period`. Rejected until an external
valuation source exists.

## Consequences
- **`fact_player_club_period`** is the consumption-layer model for club
  stints; join pattern documented in `docs/case-study.md`
- **`dbt snapshot`** is a separate operational step from model builds;
  orchestration must schedule snapshot runs after squad / team_seasons ingest
- Data quality can compare open stint in `fact_player_club_period` vs
  current row in `scd_player_club` when they diverge (transfer missing or
  squad lag)
- No `scd_club_coach` (ADR 009); no transfer SCD to maintain in parallel
  with periods
- Downstream docs and marts README state that dashboards use `dim_*` +
  `fact_*` only — not snapshots

## Related
- `models/core/fact_player_club_period.sql`
- `models/intermediate/int_player_club_periods.sql`
- `snapshots/scd_player_club.sql`, `snapshots/scd_club_league.sql`
- ADR 009: Drop Coach Models (no `scd_club_coach`)
- ADR 010: Transfers Wider Composite Key (tie-breaker on ambiguous API rows;
  periods must join on full keys where possible)
