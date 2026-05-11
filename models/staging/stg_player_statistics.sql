{{ config(materialized='incremental',
    unique_key=['fixture_id', 'team_id', 'player_id'],
    incremental_strategy='merge'
) }}

with source as (
    select
        -- identifiers
        fixture_id,
        team_id,
        player_id,
        -- player details
        trim(team_name) as team_name,
        trim(player_name) as player_name,
        jersey_number,
        trim(position) as player_position,
        rating,
        is_captain,
        is_substitute,
        -- statistics
        minutes_played,
        offsides,
        shots_total as total_shots,
        shots_on_target,
        goals_scored as total_goals_scored,
        goals_conceded as total_goals_conceded,
        assists,
        saves,
        passes_total as total_passes,
        passes_key as key_passes,
        trim(pass_accuracy) as pass_accuracy_pct,
        tackles_total as total_tackles,
        blocks,
        interceptions,
        duels_total as total_duels,
        duels_won,
        dribbles_attempted,
        dribbles_success as successful_dribbles,
        dribbles_past,
        fouls_drawn,
        fouls_committed,
        yellow_cards as yellow_card_count,
        red_cards as red_card_count,
        penalty_won as penalties_won,
        penalty_committed as penalties_committed,
        penalty_scored as penalties_scored,
        penalty_missed as penalties_missed,
        penalty_saved as penalties_saved,
        -- metadata
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_player_statistics') }}
    {% if is_incremental() %}
        where ingested_at > (select max(ingested_at) from {{ this }})
    {% endif %}
)

select * from source
