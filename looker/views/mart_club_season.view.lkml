view: mart_club_season {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_club_season` ;;

  dimension: team_id {
    type: number
    sql: ${TABLE}.team_id ;;
    primary_key: yes
    hidden: yes
  }

  dimension: league_id {
    type: number
    sql: ${TABLE}.league_id ;;
    hidden: yes
  }

  dimension: team_name {
    type: string
    sql: ${TABLE}.team_name ;;
    label: "Club"
  }

  dimension: league_name {
    type: string
    sql: ${TABLE}.league_name ;;
    label: "League"
  }

  dimension: league_season {
    type: number
    sql: ${TABLE}.league_season ;;
    label: "Season"
  }

  measure: total_matches {
    type: sum
    sql: ${TABLE}.matches_played ;;
    label: "Matches played"
  }

  measure: total_league_points {
    type: sum
    sql: ${TABLE}.league_points ;;
    label: "League points"
  }

  measure: total_goals_scored {
    type: sum
    sql: ${TABLE}.goals_scored ;;
    label: "Goals scored"
  }

  measure: total_goals_conceded {
    type: sum
    sql: ${TABLE}.goals_conceded ;;
    label: "Goals conceded"
  }

  measure: avg_points_per_game {
    type: average
    sql: ${TABLE}.points_per_game ;;
    label: "Avg points per game"
    value_format_name: decimal_2
  }
}
