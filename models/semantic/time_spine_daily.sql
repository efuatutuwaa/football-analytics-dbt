{{
    config(
        materialized='table',
        tags=['metricflow', 'time_spine'],
    )
}}

-- MetricFlow daily calendar (2020–2031). Required when semantic_models YAML exists under models/.
-- See models/semantic/_time_spine.yml and models/semantic/README.md

with days as (
    {{ dbt.date_spine(
        datepart='day',
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2031-12-31' as date)"
    ) }}
)

select cast(date_day as date) as date_day
from days
