# Marts layer (`football_marts`)

Reporting models for BI, Streamlit, and portfolio demos.

- **Full spec per model:** comment block at the top of each `mart_*.sql` (grain, sources, logic, excludes).
- **Shared SQL idioms:** this file — so you do not have to reverse-engineer `GROUP BY` / window logic in every model.
- **Tests only:** `schema.yml` (uniqueness on grain keys).

## Consumption rule

Join **`dim_*`** and **`fact_*`** (or other marts) — never **`int_*`** or **snapshots** from dashboards.

## UCL round labels (API-Football vs UEFA)

From **2024–25**, the Champions League uses a **36-team league phase** (8 matches), then knockouts. API-Football `league_round` text does not always match [UEFA](https://www.uefa.com) wording.

| API-Football (`league_round`) | UEFA / display (`league_round_display`) | Notes |
|------------------------------|----------------------------------------|--------|
| `League Stage - 1` … `League Stage - 8` | **League phase** | One row per matchday in facts; mart `farthest_round` uses display label |
| `Round of 32` | **Knockout round play-offs** | Same stage as `Knockout Round Play-offs` — teams **9th–24th** in the UCL league phase (2 legs) |
| `Knockout Round Play-offs` | **Knockout round play-offs** | |
| `Round of 16` … `Final` | Unchanged | Top **8** in league phase skip play-offs (e.g. Arsenal → 14 matches to SF) |

**Where it is implemented**

- Macro: `macros/normalize_european_club_round.sql`
- `int_club_intl_runs` → `fact_club_intl_run.league_round_display`
- `mart_club_european_performance.farthest_round` (display) and `farthest_round_api` (raw)

**Rebuild after label changes:** `dbt run --select int_club_intl_runs fact_club_intl_run mart_club_european_performance`

## Which model uses which pattern

| Model | Patterns (see below) |
|-------|----------------------|
| `mart_club_domestic_cup_performance` | A, B, C, D |
| `mart_club_european_performance` | A, B, C, D, E |
| `mart_national_team_results` | A, B, C, E, F |
| `mart_national_team_honours` | G |
| `mart_club_honours` | H, I |
| `mart_world_cup` | A, B, J |
| `mart_continental_cups` | A, B, J |
| `mart_club_season` | — (thin passthrough + derived) |
| `mart_player_season` | — (thin passthrough + derived) |
| `mart_player_matchday` | A, K |
| `mart_player_valuation` | L |
| `mart_player_value_changes` | L, M |
| `mart_transfer_window` | — (thin passthrough + date parts) |
| `mart_league_standings` | G-style filter (domestic league_ids only) |
| `mart_club_matchday` | A, K |
| `mart_club_squad_value` | C, L |
| `mart_league_week` | A, C |
| `mart_domestic_league_top_scorers` | P |

---

## SQL patterns

### A — Finished matches only

```sql
where match_status_short in ('FT', 'AET', 'PEN')
```

W/D/L and goal totals only count **completed** matches. Unplayed or live fixtures are excluded before aggregation.

**Used in:** all campaign and round marts, `mart_club_matchday`, `mart_league_week`, except `mart_club_honours` (finals filter on facts) and `mart_national_team_honours` (inherits from results mart).

---

### B — W/D/L from perspective + goals (not `match_result` on fact)

```sql
case
  when is_winner then 'win'
  when goals_scored = goals_conceded then 'draw'
  else 'loss'
end as match_result
```

Cup and national facts expose **`is_winner`** per team row, not a pre-built `match_result` column. Draws are rare in knockouts but possible before penalties.

**Used in:** `mart_club_domestic_cup_performance`, `mart_club_european_performance`, `mart_national_team_results`, `mart_world_cup`, `mart_continental_cups`.

---

### C — `max(column)` in `GROUP BY` (not a business “max”)

When you `group by team_id, league_id, league_season` (or add `league_round`), every other selected column must be aggregated.

| Column | Why `max()` |
|--------|-------------|
| `team_name`, `league_name` | Same on every row per `team_id` / `league_id` — pick one value |
| `ingested_at` | `max` = latest ingest in the group |
| `group_name` | `max(case when …)` — pick a non-null group label in the round bucket |

**Not** “highest alphabetical name.” Prefer joining **`dim_club`** / **`dim_national_team`** after the aggregate if you want names only from dimensions.

**Used in:** all aggregating marts (`campaign_agg`, `round_agg`, `league_titles` CTE in honours).

---

### D — `farthest_round` via `row_number() … qualify … = 1`

One **label** for the deepest round in a campaign (club cup, European run, or national edition):

```sql
qualify row_number() over (
  partition by team_id, league_id, league_season  -- omit league_id only where grain differs
  order by round_order desc, match_date desc, fixture_id desc
) = 1
```

- **`round_order desc`** — numeric depth from intermediate/fact (Final > Semi-finals > …), not string sort on `league_round`.
- **`row_number()`** — ordinal 1, 2, 3; **no tied ranks**. Unlike `rank()` / `dense_rank()`, two rows never share the same number unless you drop one via `ORDER BY`.
- **`fixture_id desc`** — breaks remaining ties (replays, two legs).

Separate from **`was_cup_winner` / `was_tournament_winner`**, which only checks **Final + is_winner**.

**Used in:** `mart_club_domestic_cup_performance`, `mart_club_european_performance` (`farthest_round_label`); `mart_national_team_results` (`farthest_round_label` + `deepest_round_match` for placement).

---

### E — Group-stage snapshot (`qualify` on latest group match)

```sql
where group_name is not null  -- or league_round like 'Group%'
qualify row_number() over (
  partition by team_id, league_id, league_season
  order by match_date desc, fixture_id desc
) = 1
```

Takes **one row** of group standings fields (position, points, etc.) — usually the last group match ingested, not a full group-stage aggregate.

**Used in:** `mart_club_european_performance`, `mart_national_team_results`.

---

### F — `tournament_placement` from deepest finished match

`mart_national_team_results` builds `deepest_round_match` (same `row_number` idea as **D**), then:

```sql
case
  when league_round = 'Final' and is_winner then 'Winner'
  when league_round = 'Final' and not is_winner then 'Runner-up'
  when league_round = 'Semi-finals' and not is_winner then 'Semi-finalist'
  ...
end as tournament_placement
```

Placement is defined **once** here. Downstream marts filter on it — they do not recompute.

**Used in:** `mart_national_team_results` only (source for **G**).

---

### G — Thin filter mart (no new logic)

```sql
select … from {{ ref('mart_national_team_results') }}
where tournament_placement in ('Winner', 'Runner-up', 'Semi-finalist')
```

Passthrough + boolean flags. Change placement rules in **results** mart, then re-run honours.

**Used in:** `mart_national_team_honours`.

---

### H — Trophy counts from multiple facts (`union` + `coalesce`)

`mart_club_honours`:

1. **CTE per trophy type** — league (`team_rank = 1`), domestic cups (`Final` + `is_winner`), European (`Final` + `is_winner`).
2. **`union`** of `(team_id, league_season)` keys so any club-season with ≥1 trophy appears.
3. **`left join`** each CTE + **`coalesce(..., 0)`** for counts.
4. **`coalesce(l.team_name, c.team_name)`** — name from league row or **`dim_club`** if only cups were won.

`count(distinct league_id)` on cup wins so two English cups in one season count as **2** toward `domestic_cups_won`.

**Do not** use **`is_farthest_round`** alone as a trophy — a team can reach the final and lose.

**Used in:** `mart_club_honours`.

---

### I — `honour_label` (`CASE` on trophy counts)

Ordered **`CASE`**: Quadruple → Treble → Double → Single → else `'None'`. Rows with **`total_trophies = 0`** are dropped in `WHERE`; rows with trophies but no league+cup combo can still show **`honour_label = 'None'`** (e.g. two cups, no league title).

Definitions are in the **`mart_club_honours.sql`** header (England two-cup aware).

**Used in:** `mart_club_honours`.

---

### J — Round-by-round mart (`group by` includes `league_round`)

`round_agg` groups by **`team_id`, `league_season`, `league_round`** (plus `league_id` on continental). One row per **round stage** per edition, not one row per edition.

`team_max_round` = `max(round_order)` per edition. Flags:

- **`is_eliminated_in_round`** — this row’s `round_order` equals edition max **and** `losses > 0` in that round bucket (heuristic exit).
- **`is_winner_in_round`** — `league_round = 'Final'` and `wins > 0` in that bucket.

A nation has **multiple rows** per edition (Group, R16, QF, …).

**Used in:** `mart_world_cup` (`league_id = 1`), `mart_continental_cups` (v1: `league_id = 4`).

---

### K — Rolling form (`rows between 4 preceding and current row`)

On finished domestic league matches ordered by `match_date`, `fixture_id`:

```sql
sum(match_points) over (
  partition by team_id, league_id, league_season
  order by match_date, fixture_id
  rows between 4 preceding and current row
) as rolling_points_last_5
```

`match_points`: win = 3, draw = 1, loss = 0 (from `match_result` on `fact_club_match_stats`).

**Why “last 5” = 4 preceding + current row**

| Matches played in season (in order) | Rows in the window for that fixture |
|-------------------------------------|-------------------------------------|
| 1st | 1 (current only) |
| 2nd | 2 |
| … | … |
| 5th+ | 5 (four prior + current) |

- **Current row is included** — form on that row is “including this result” (post-match / same-row semantics). For pre-kickoff form, use `rows between 4 preceding and 1 preceding` instead (not implemented in v1).
- **Scope:** same `team_id × league_id × league_season`, finished domestic league matches only (pattern A). Not “last 5 across all competitions.”
- **Why 5:** common dashboard shorthand; change `4 preceding` to `N-1 preceding` for a different N.
- **Player variant (`mart_player_matchday`):** partition by `player_id, team_id, league_id, league_season` so mid-season transfers reset the window per club stint.

**Used in:** `mart_club_matchday`, `mart_player_matchday`.

---

### L — Transfer fee parse (EUR estimate from API string)

```sql
{{ parse_transfer_fee_eur('transfer_fee') }} as transfer_fee_eur
```

Macro: `macros/parse_transfer_fee_eur.sql` — uses `try_cast` so malformed or non-numeric fee strings become `null` instead of failing the run.

Assumes fees like `€ 75M` / `€ 500K`. Not a substitute for official market-value snapshots.

**Used in:** `mart_club_squad_value`, `mart_player_valuation` (inbound + global fallback at player-season grain).

---

### M — Transfer fee change (`lag` on player timeline)

Order fee-bearing moves per `player_id` by `transfer_date`, `ingested_at`, then:

```sql
lag(transfer_fee_eur) over (
  partition by player_id
  order by transfer_date, ingested_at
) as prior_transfer_fee_eur
```

`fee_change_eur = current - prior`; `fee_change_pct` when prior > 0. First move per player has null prior and null deltas.

**Used in:** `mart_player_value_changes`.

---

### P — Leaderboard `dense_rank` (ties share rank)

Within `league_id × league_season`, rank each **club stint** row (not summed across mid-season transfers):

```sql
dense_rank() over (
  partition by league_id, league_season
  order by goals desc, assists desc, player_id
) as goals_rank
```

Use **`dense_rank()`** (not `rank()`) so tied scorers share a position with no gap (1, 2, 2, 3). Add **`player_id`** (or `team_id`) as final `order by` tie-break so ranks are deterministic.

**Used in:** `mart_domestic_league_top_scorers`.

---

## Models

| Model | Grain | Primary source |
|-------|-------|----------------|
| [mart_club_domestic_cup_performance](mart_club_domestic_cup_performance.sql) | club × cup × season | `fact_club_domestic_cup_run` |
| [mart_club_european_performance](mart_club_european_performance.sql) | club × tournament × season | `fact_club_intl_run` |
| [mart_national_team_results](mart_national_team_results.sql) | nation × tournament × season | `fact_national_team_run` |
| [mart_national_team_honours](mart_national_team_honours.sql) | podium editions only | `mart_national_team_results` |
| [mart_club_honours](mart_club_honours.sql) | club × season (≥1 trophy) | standings + cup/intl facts |
| [mart_world_cup](mart_world_cup.sql) | nation × WC season × round | `fact_national_team_run` |
| [mart_continental_cups](mart_continental_cups.sql) | nation × tournament × season × round | `fact_national_team_run` |
| [mart_club_season](mart_club_season.sql) | club × domestic league × season | `fact_club_season` |
| [mart_player_season](mart_player_season.sql) | player × club × league × season | `fact_player_season` |
| [mart_player_matchday](mart_player_matchday.sql) | player × finished league appearance | `fact_player_match_stats`, `fact_fixture` |
| [mart_player_valuation](mart_player_valuation.sql) | player × club × league × season | `mart_player_season`, `fact_player_market_value_period` |
| [mart_player_value_changes](mart_player_value_changes.sql) | fee-bearing transfer | `fact_player_market_value_period` |
| [mart_transfer_window](mart_transfer_window.sql) | fee-bearing transfer | `fact_player_market_value_period` |
| [mart_league_standings](mart_league_standings.sql) | team × domestic league × season × group | `fact_standings` |
| [mart_club_matchday](mart_club_matchday.sql) | club × finished league fixture | `fact_club_match_stats` |
| [mart_club_squad_value](mart_club_squad_value.sql) | club × domestic league × season | `mart_player_season`, `fact_player_market_value_period` |
| [mart_league_week](mart_league_week.sql) | league × season × matchweek | `fact_fixture` |
| [mart_domestic_league_top_scorers](mart_domestic_league_top_scorers.sql) | player × club × domestic league × season | `mart_player_season`, `dim_player` |

```bash
dbt run --select path:models/marts
dbt test --select path:models/marts
```
