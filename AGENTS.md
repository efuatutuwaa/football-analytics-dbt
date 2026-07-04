# AGENTS.md

## Cursor Cloud specific instructions

This repo is a football-analytics **monorepo** with three independently-runnable components plus BI definitions. See `README.md` for the full architecture.

### Components and how to run them

| Component | Path | Runtime | External deps needed to actually work? |
|---|---|---|---|
| dbt warehouse project | root (`models/`, `snapshots/`, `macros/`) | Python `.venv` + `dbt-databricks` | Yes — needs a live Databricks workspace + `~/.dbt/profiles.yml`. |
| Python/PySpark ingestion + ops scripts | `scripts/` | Python `.venv` | Yes — needs Databricks creds and `API_FOOTBALL_KEY`. |
| Streamlit dashboard | `app/` | Python `app/app-env` venv | Yes — needs Databricks SQL warehouse with marts already built. |
| Next.js portfolio site | `portfolio-site/` | Node/npm | **No — fully standalone**, runs with zero external creds. |

### Key environment facts (non-obvious)

- **No local database exists.** dbt, ingestion, and Streamlit all target an external **Databricks** workspace. Without Databricks credentials they install and parse/lint fine but cannot run end-to-end. The `portfolio-site` is the only component that runs fully locally.
- Python deps live in **two separate venvs**: root `.venv` (dbt + ingestion + sqlfluff + flake8) and `app/app-env` (Streamlit). `app/pyrightconfig.json` expects the venv named `app-env` inside `app/`.
- `python3.12-venv` is a system prerequisite for creating the venvs (installed during environment setup via apt).
- **dbt commands need a profile.** Even `dbt parse` requires `~/.dbt/profiles.yml` with profile `football_analytics`. For credential-free validation, create a stub profile (see `.github/workflows/dbt-ci.yml` for the exact shape) — `dbt deps` and `dbt parse` then succeed. `dbt run`/`dbt test` require real Databricks creds.
- **sqlfluff is very slow.** It uses the dbt templater, so linting even a single `.sql` file compiles the whole dbt project (~5 min per invocation). Expect long runtimes; don't assume it hung.
- `next lint` prompts interactively when no ESLint config is committed — avoid it in CI/automation. `npm run build` runs ESLint + type-checking non-interactively, so use the build for lint/type validation of `portfolio-site`.
- Root `README.md` references `scripts/ingestion/requirements.txt`, but that file does not exist; root `requirements.txt` covers ingestion deps.

### Lint / test / build / run commands

- Portfolio site (standalone): `cd portfolio-site && npm run dev` (http://localhost:3000), `npm run build`.
- dbt validation: `.venv/bin/dbt deps` then `.venv/bin/dbt parse` (needs stub or real `~/.dbt/profiles.yml`).
- Python lint (matches CI): `.venv/bin/flake8 scripts/ --max-line-length=120 --ignore=W503`.
- SQL lint: `.venv/bin/sqlfluff lint models/...` (slow, see note above).
- Streamlit: `cd app && ./app-env/bin/streamlit run streamlit_app.py` (needs Databricks creds in `app/.env`).
