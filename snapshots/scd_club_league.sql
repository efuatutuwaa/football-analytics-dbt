{% snapshot scd_club_league %}

{{
    config(
        target_schema='football_core',
        unique_key=['team_id', 'season_year'],
        strategy='check',
        check_cols=['league_id', 'league_name'],
    )
}}

/*
  Type 2 audit of domestic league participation per club per season.
  Source: stg_team_seasons + stg_leagues (league_type = league) + stg_teams (clubs only).

  Analytic participation spine remains int_club_league_periods (same filters, no dbt_valid_*).
  Use this snapshot for: API corrections to league_id, audit trail on re-ingest.

  Run: dbt snapshot --select scd_club_league
*/

select
    ts.team_id,
    t.team_name,
    ts.league_id,
    l.league_name,
    ts.season_year,
    ts.ingested_at
from {{ ref('stg_team_seasons') }} as ts
inner join {{ ref('stg_leagues') }} as l
    on ts.league_id = l.league_id
    and l.league_type = 'league'
inner join {{ ref('stg_teams') }} as t
    on ts.team_id = t.team_id
    and t.is_national_team = false

{% endsnapshot %}
