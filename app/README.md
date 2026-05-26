# Streamlit app

Interactive demo over **`football_marts`** — same consumption rule as Looker and MetricFlow (no `int_*`, no snapshots).

## Pages

| Page | Mart(s) |
|------|---------|
| Club season | `mart_club_season` + `dim_club` (logos) |
| Player season | `mart_player_season` + `dim_player` (photos) |
| European club | `mart_club_european_performance` + `dim_club` (logos) |
| Transfers | `mart_player_value_changes` + destination league from `mart_player_season` |
| Club honours | `mart_club_honours` + `dim_club` (logos) |
| National team honours | `mart_national_team_honours` + `dim_national_team` (flags) |
| Club squad value | `mart_club_squad_value` + `dim_club` (logos) |
| Ops pipeline | `mart_pipeline_health`, `mart_api_usage` (`football_ops`) |

## Run locally

```bash
cd app
python3 -m venv app-env
source app-env/bin/activate   # Windows: app-env\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # edit with your warehouse credentials
streamlit run streamlit_app.py
```

Load env vars automatically (optional):

```bash
export $(grep -v '^#' .env | xargs)
```

## Prerequisites

- `dbt run --select path:models/marts path:models/ops` completed on Databricks
- SQL warehouse access with read on `football_marts`, `football_core` (dims for images), and `football_ops`

## Extend

- Add charts (`st.line_chart`, Plotly) on existing queries
- Transfer timeline: join `fact_player_club_period` from `football_core`
- Do not query `football_intermediate` from this app
