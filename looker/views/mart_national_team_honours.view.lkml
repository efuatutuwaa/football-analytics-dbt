view: mart_national_team_honours {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_national_team_honours` ;;

  dimension: honour_grain_key {
    type: string
    primary_key: yes
    hidden: yes
    sql: concat(cast(${TABLE}.team_id as string), '-', cast(${TABLE}.league_id as string), '-', cast(${TABLE}.league_season as string)) ;;
  }

  dimension: team_id {
    type: number
    sql: ${TABLE}.team_id ;;
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
    label: "Nation"
  }

  dimension: league_name {
    type: string
    sql: ${TABLE}.league_name ;;
    label: "Tournament"
  }

  dimension: league_season {
    type: number
    sql: ${TABLE}.league_season ;;
    label: "Tournament year"
  }

  dimension: tournament_placement {
    type: string
    sql: ${TABLE}.tournament_placement ;;
    label: "Placement"
  }

  dimension: is_winner {
    type: yesno
    sql: ${TABLE}.is_winner ;;
    label: "Winner"
  }

  dimension: is_runner_up {
    type: yesno
    sql: ${TABLE}.is_runner_up ;;
    label: "Runner-up"
  }

  dimension: is_semi_finalist {
    type: yesno
    sql: ${TABLE}.is_semi_finalist ;;
    label: "Semi-finalist"
  }

  measure: podium_finishes {
    type: count
    label: "Podium finishes"
  }

  measure: tournament_wins {
    type: count
    filters: [is_winner: "yes"]
    label: "Tournament wins"
  }

  measure: total_goals_scored {
    type: sum
    sql: ${TABLE}.goals_scored ;;
    label: "Goals scored (edition)"
  }

  measure: total_goals_conceded {
    type: sum
    sql: ${TABLE}.goals_conceded ;;
    label: "Goals conceded (edition)"
  }
}
