# ADR 010: Transfers - Wider Composite Key and Downstream Tie-Breaker for Residual Ambiguity

## Date
2026-05-15

## Status
Accepted

## Context
During staging layer testing, `stg_transfers` failed its uniqueness test.
Investigation via Databricks queries revealed 691 duplicate rows across
105,318 total rows (0.71%).

Two distinct types of duplicates were identified:

**Type 1 — API ambiguity**
The same transfer event appears with two different `team_out_id` values.
This occurs when the API cannot unambiguously determine the previous club
(e.g. a player who was on loan and whose "parent club" is unclear). These
are not exact copies — they differ on `team_out_id` and represent the
API returning two plausible interpretations of the same move.

**Type 2 — Ingestion double-write**
Exact copy rows where all columns including `team_out_id` are identical.
These are caused by the ingestion script running twice against the same
API response window — a known bug in the transfer fetch script.

Duplicates were concentrated in English cup competitions and Coupe de France,
where loan and short-term registration patterns are more ambiguous.

## Decision
Deduplicate in `stg_transfers` using a wider composite key:

```sql
qualify row_number() over (
    partition by player_id, transfer_date, team_in_id, team_out_id
    order by ingested_at desc
) = 1
```

This removes Type 2 (exact copy) duplicates by keeping the latest ingestion,
while preserving Type 1 (API ambiguity) rows since they differ on `team_out_id`.

Column aliases were introduced to improve clarity:
- `team_in_id` → `new_team_id`
- `team_in_name` → `new_team_name`
- `team_out_id` → `previous_team_id`
- `team_out_name` → `previous_team_name`

The uniqueness test in `schema.yml` was updated to match the wider composite
key: `(player_id, transfer_date, new_team_id, previous_team_id)`.

## Alternatives Considered
**Narrower composite key `(player_id, transfer_date, team_in_id)`** — would
collapse both duplicate types including the API ambiguity variants. Rejected
because it silently discards one of two plausible API interpretations, losing
information that may be meaningful for certain players and clubs.

**Fix the ingestion script double-write bug** — the correct long-term fix for
Type 2 duplicates. Not addressed here as it is out of scope for the dbt layer.
The ingestion bug is tracked separately.

## Consequences
- Type 2 (exact copy) duplicates are fully resolved in `stg_transfers`
- Type 1 (API ambiguity) rows are preserved — a small number of players
  will have two transfer records for the same move with different previous clubs
- Downstream models (`int_player_club_periods`, `int_player_market_value_periods`)
  must apply a tie-breaker when joining on `(player_id, transfer_date)` alone
  to avoid fan-out — prefer joining on the full composite key where possible
- The ingestion double-write bug in the transfer script remains open and should
  be fixed to prevent Type 2 duplicates from re-accumulating over time
