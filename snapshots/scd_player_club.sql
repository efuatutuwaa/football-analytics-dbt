{% snapshot scd_player_club %}

{{
    config(
        target_schema='football_core',
        unique_key='player_id',
        strategy='check',
        check_cols=['team_id', 'team_name', 'jersey_number', 'player_position'],
    )
}}

/*
  Type 2 audit of squad roster as returned by the API on each snapshot run.
  Source: stg_team_squads (current squad per team_id + player_id).

  Not a substitute for transfer history — use fact_player_club_period (transfer-derived stints).
  Use this snapshot for: roster drift without a transfer row, DQ, re-ingest corrections.

  Run: dbt snapshot --select scd_player_club
*/

select
    player_id,
    player_name,
    team_id,
    team_name,
    jersey_number,
    player_position
from {{ ref('stg_team_squads') }}
qualify row_number() over (
    partition by player_id
    order by ingested_at desc
) = 1

{% endsnapshot %}
