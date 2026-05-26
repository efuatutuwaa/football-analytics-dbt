view: mart_club_european_performance {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_club_european_performance` ;;

  dimension: campaign_grain_key {
    type: string
    primary_key: yes
    hidden: yes
    sql: concat(
      cast(${TABLE}.team_id as string), '-',
      cast(${TABLE}.league_id as string), '-',
      cast(${TABLE}.league_season as string)
    ) ;;
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
    label: "Club"
  }

  dimension: league_name {
    type: string
    sql: ${TABLE}.league_name ;;
    label: "Competition"
  }

  dimension: league_season {
    type: number
    sql: ${TABLE}.league_season ;;
    label: "Season"
  }

  dimension: farthest_round {
    type: string
    sql: ${TABLE}.farthest_round ;;
    label: "Farthest round (UEFA label)"
  }

  dimension: farthest_round_api {
    type: string
    sql: ${TABLE}.farthest_round_api ;;
    label: "Farthest round (API raw)"
    hidden: yes
  }

  dimension: group_name {
    type: string
    sql: ${TABLE}.group_name ;;
    label: "Group"
  }

  dimension: was_tournament_winner {
    type: yesno
    sql: ${TABLE}.was_tournament_winner ;;
    label: "Tournament winner"
  }

  measure: campaigns {
    type: count
    label: "Campaigns"
  }

  measure: total_matches_played {
    type: sum
    sql: ${TABLE}.matches_played ;;
    label: "Matches played"
  }

  measure: total_wins {
    type: sum
    sql: ${TABLE}.wins ;;
    label: "Wins"
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

  measure: tournament_wins {
    type: count
    filters: [was_tournament_winner: "yes"]
    label: "Tournament wins"
  }
}
