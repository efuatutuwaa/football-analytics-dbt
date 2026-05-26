-- Model: stg_countries
-- Layer: staging
-- Grain: 1 row per country (country_name is the natural key)
-- Materialization: view — rebuilt from raw on each dbt run
-- Source: football_raw.raw_countries
-- Purpose:
--   Reference list of countries returned by API-Football (names, ISO codes, flag URLs).
--   Used to enrich dim_club and dim_national_team when team_country matches country_name.
-- Transformations:
--   Casts ingested_at to timestamp; passes through country_name, country_code, country_flag_url.
-- Downstream:
--   dim_club, dim_national_team (left join on team_country = country_name)
-- Notes:
--   country_code may be null for some regional or composite entries in the API.

{{ config(materialized='view') }}

with source as (
    select
        country_name,
        country_code,
        country_flag_url,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('football_raw', 'raw_countries') }}
)

select * from source
