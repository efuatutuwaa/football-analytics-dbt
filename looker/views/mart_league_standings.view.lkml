view: mart_league_standings {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_league_standings` ;;

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

  dimension: team_rank {
    type: number
    sql: ${TABLE}.team_rank ;;
    label: "Rank"
  }

  dimension: standing_status {
    type: string
    sql: ${TABLE}.standing_status ;;
    label: "Status"
  }

  dimension: form {
    type: string
    sql: ${TABLE}.form ;;
    label: "Form (API string)"
  }

  measure: total_points {
    type: sum
    sql: ${TABLE}.team_points ;;
    label: "Points"
  }

  measure: total_goals_for {
    type: sum
    sql: ${TABLE}.goals_for ;;
    label: "Goals for"
  }

  measure: total_goals_against {
    type: sum
    sql: ${TABLE}.goals_against ;;
    label: "Goals against"
  }

  measure: avg_win_rate {
    type: average
    sql: ${TABLE}.win_rate ;;
    label: "Avg win rate"
    value_format_name: percent_1
  }

  measure: clubs_count {
    type: count
    label: "Clubs"
  }
}
