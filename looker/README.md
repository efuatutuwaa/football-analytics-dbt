# LookML (Looker)

LookML for reviewers and hiring managers — **readable without a Looker instance**. Wire `connection` and `sql_table_name` to your Databricks catalog when you deploy.

## Layout

| File | Role |
|------|------|
| `football.model.lkml` | Connection, explores, joins |
| `views/mart_club_season.view.lkml` | Club domestic season |
| `views/mart_player_season.view.lkml` | Player season (full stat line + 5+/10+ goal filters) |
| `views/mart_transfer_window.view.lkml` | Fee-bearing transfers (raw fee string) |
| `views/mart_player_value_changes.view.lkml` | Fee moves with EUR and deltas |
| `views/mart_league_standings.view.lkml` | Domestic league table snapshot |
| `views/mart_national_team_honours.view.lkml` | WC/Euros podium (Winner, Runner-up, Semi) |
| `views/mart_club_honours.view.lkml` | Club trophy cabinet per season |
| `views/mart_club_european_performance.view.lkml` | UCL / CWC campaign summary per club |

## Setup

1. Create a Looker **Databricks** connection pointing at your warehouse.
2. Set Looker constant `football_catalog` (e.g. `main`) and `football_marts_schema` (e.g. `football_marts`) in the model file or Admin → Constants.
3. Point the model at this repo (`looker/` as project root or synced from Git).

## Consumption rule

Explores use **`football_marts`** tables only — same as Streamlit and MetricFlow demo set. Do not explore `int_*` or snapshot tables for reporting.

## Related

- Warehouse grains: [`../models/marts/README.md`](../models/marts/README.md)
- MetricFlow: [`../models/semantic/README.md`](../models/semantic/README.md)
