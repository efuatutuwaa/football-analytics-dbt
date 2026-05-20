# ADR 005: Skipped Team Statistics Endpoint

## Date
2026-04-14

## Status
Accepted

## Context
API-Football provides a /teams/statistics endpoint that returns
aggregated season statistics per team per league including:

- Fixtures played, wins, draws, losses
- Goals for and against
- Clean sheets
- Form string
- Biggest wins and losses
- Card statistics by minute
- Lineup formations used

I had to decide whether to ingest this endpoint or derive these
metrics myself in the dbt intermediate layer.

## Decision
I chose to skip the /teams/statistics endpoint entirely and derive
all team level metrics in the dbt intermediate layer from raw
fixture and player statistics data.

Team level metrics are calculated in:
- int_club_matchday_metrics — per match aggregations
- int_club_season_metrics — per season aggregations

Both models source from:
- raw_fixtures — match results
- raw_fixture_events — goals, cards, substitutions
- raw_fixture_statistics — shots, possession, passes
- raw_player_statistics — individual player contributions

## Alternatives Considered
**Ingest /teams/statistics directly** — simpler, pre-aggregated
data available immediately. Rejected because:
- It trusts the API's aggregation logic as a black box
- If the API changes its calculation method numbers become
  inconsistent with historical data
- Deriving metrics in dbt follows the SSOT principle —
  one place where metric logic is defined and owned
- Pre-aggregated data cannot be re-aggregated to different
  grains without risk of double counting

## Consequences
- More complex intermediate layer — metrics must be derived
  from granular data
- Full control over metric definitions and aggregation logic
- Consistent numbers across all layers — no discrepancy between
  API aggregations and dbt calculations
- Follows the dbt best practice of defining metrics at the most
  granular level (SSOT) and aggregating upward via int_*_metrics models
- Easier to test and validate — each metric has a clear
  definition in dbt YAML
