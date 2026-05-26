{#-
  Map API-Football league_round strings to UEFA-style display labels (UCL / CWC).
  Raw values are kept in league_round; use league_round_display in marts and BI.

  See models/marts/README.md § UCL round labels (API vs UEFA).
-#}
{% macro normalize_european_club_round(league_round_column) %}
    case
        when {{ league_round_column }} in ('Round of 32', 'Knockout Round Play-offs')
            then 'Knockout round play-offs'
        when {{ league_round_column }} like 'League Stage%'
            then 'League phase'
        when {{ league_round_column }} like 'Group Stage%' or {{ league_round_column }} like 'Group %'
            then 'Group stage'
        else {{ league_round_column }}
    end
{% endmacro %}
