view: mart_club_honours {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_club_honours` ;;

  dimension: honour_grain_key {
    type: string
    primary_key: yes
    hidden: yes
    sql: concat(cast(${TABLE}.team_id as string), '-', cast(${TABLE}.league_season as string)) ;;
  }

  dimension: team_id {
    type: number
    sql: ${TABLE}.team_id ;;
    hidden: yes
  }

  dimension: team_name {
    type: string
    sql: ${TABLE}.team_name ;;
    label: "Club"
  }

  dimension: league_season {
    type: number
    sql: ${TABLE}.league_season ;;
    label: "Season"
  }

  dimension: honour_label {
    type: string
    sql: ${TABLE}.honour_label ;;
    label: "Honour label"
  }

  measure: total_trophies {
    type: sum
    sql: ${TABLE}.total_trophies ;;
    label: "Total trophies"
  }

  measure: league_titles_won {
    type: sum
    sql: ${TABLE}.league_titles_won ;;
    label: "League titles"
  }

  measure: domestic_cups_won {
    type: sum
    sql: ${TABLE}.domestic_cups_won ;;
    label: "Domestic cups"
  }

  measure: european_trophies_won {
    type: sum
    sql: ${TABLE}.european_trophies_won ;;
    label: "European trophies"
  }

  measure: honour_seasons {
    type: count
    label: "Honour seasons"
  }

  measure: treble_seasons {
    type: count
    filters: [honour_label: "Treble"]
    label: "Treble seasons"
  }

  measure: quadruple_seasons {
    type: count
    filters: [honour_label: "Quadruple"]
    label: "Quadruple seasons"
  }
}
