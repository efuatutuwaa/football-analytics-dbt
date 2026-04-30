{{ config(materialized='table') }}

with source as (
    select
        -- identifiers
        league_id,
        trim(league_name) as league_name,
        league_season,
        team_id,
        trim(team_name) as team_name,
        -- standing position
        rank as team_rank,
        points as team_points,
        goals_diff as goals_difference,
        group_name,
        form,
        status as standing_status,
        description as standing_description,
        -- overall record
        all_played as matches_played,
        all_wins as matches_won,
        all_draws as matches_drawn,
        all_losses as matches_lost,
        all_goals_for as goals_for,
        all_goals_against as goals_against,
        -- home record
        home_played as home_matches_played,
        home_wins as home_matches_won,
        home_draws as home_matches_drawn,
        home_losses as home_matches_lost,
        home_goals_for,
        home_goals_against,
        -- away record
        away_played as away_matches_played,
        away_wins as away_matches_won,
        away_draws as away_matches_drawn,
        away_losses as away_matches_lost,
        away_goals_for,
        away_goals_against,
        -- metadata
        cast(last_updated as timestamp) as last_updated,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_standings') }}
)

select * from source
