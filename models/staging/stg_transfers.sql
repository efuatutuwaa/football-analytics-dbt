{{ config(materialized='view') }}

with source as (
    select
        -- identifiers
        player_id,
        -- player details
        trim(player_name) as player_name,
        -- transfer details
        transfer_date,
        trim(transfer_type) as transfer_type,
        team_in_id as new_team_id,
        trim(team_in_name) as new_team_name,
        team_out_id as previous_team_id,
        trim(team_out_name) as previous_team_name,
        -- metadata
        cast(last_updated as timestamp) as last_updated,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_transfers') }}
)

select * from source
