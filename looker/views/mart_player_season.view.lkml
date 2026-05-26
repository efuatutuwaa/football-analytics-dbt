view: mart_player_season {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_player_season` ;;

  dimension: player_season_grain_key {
    type: string
    primary_key: yes
    hidden: yes
    sql: concat(
      cast(${TABLE}.player_id as string), '-',
      cast(${TABLE}.team_id as string), '-',
      cast(${TABLE}.league_id as string), '-',
      cast(${TABLE}.league_season as string)
    ) ;;
  }

  dimension: player_id {
    type: number
    sql: ${TABLE}.player_id ;;
    hidden: yes
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

  dimension: player_name {
    type: string
    sql: ${TABLE}.player_name ;;
    label: "Player"
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

  dimension: appearances {
    type: number
    sql: ${TABLE}.appearances ;;
    label: "Appearances"
    hidden: yes
  }

  dimension: goals {
    type: number
    sql: ${TABLE}.goals ;;
    label: "Goals"
    hidden: yes
  }

  dimension: goals_per_90 {
    type: number
    sql: ${TABLE}.goals_per_90 ;;
    label: "Goals per 90"
    hidden: yes
  }

  dimension: assists_per_90 {
    type: number
    sql: ${TABLE}.assists_per_90 ;;
    label: "Assists per 90"
    hidden: yes
  }

  dimension: avg_rating {
    type: number
    sql: ${TABLE}.avg_rating ;;
    label: "Avg rating"
    hidden: yes
  }

  measure: player_season_rows {
    type: count
    label: "Player-season rows"
  }

  measure: total_goals {
    type: sum
    sql: ${TABLE}.goals ;;
    label: "Goals"
  }

  measure: total_assists {
    type: sum
    sql: ${TABLE}.assists ;;
    label: "Assists"
  }

  measure: total_appearances {
    type: sum
    sql: ${TABLE}.appearances ;;
    label: "Appearances"
  }

  measure: total_starts {
    type: sum
    sql: ${TABLE}.total_starts ;;
    label: "Starts"
  }

  measure: total_minutes_played {
    type: sum
    sql: ${TABLE}.minutes_played ;;
    label: "Minutes played"
  }

  measure: total_shots {
    type: sum
    sql: ${TABLE}.total_shots ;;
    label: "Shots"
  }

  measure: total_shots_on_target {
    type: sum
    sql: ${TABLE}.shots_on_target ;;
    label: "Shots on target"
  }

  measure: total_yellow_cards {
    type: sum
    sql: ${TABLE}.yellow_cards ;;
    label: "Yellow cards"
  }

  measure: total_red_cards {
    type: sum
    sql: ${TABLE}.red_cards ;;
    label: "Red cards"
  }

  measure: total_passes {
    type: sum
    sql: ${TABLE}.total_passes ;;
    label: "Passes"
  }

  measure: total_tackles {
    type: sum
    sql: ${TABLE}.total_tackles ;;
    label: "Tackles"
  }

  measure: total_interceptions {
    type: sum
    sql: ${TABLE}.interceptions ;;
    label: "Interceptions"
  }

  measure: total_successful_dribbles {
    type: sum
    sql: ${TABLE}.successful_dribbles ;;
    label: "Successful dribbles"
  }

  measure: avg_goals_per_90 {
    type: average
    sql: ${TABLE}.goals_per_90 ;;
    label: "Avg goals per 90"
    value_format_name: decimal_2
  }

  measure: avg_assists_per_90 {
    type: average
    sql: ${TABLE}.assists_per_90 ;;
    label: "Avg assists per 90"
    value_format_name: decimal_2
  }

  measure: avg_match_rating {
    type: average
    sql: ${TABLE}.avg_rating ;;
    label: "Avg match rating"
    value_format_name: decimal_2
  }

  measure: avg_shot_conversion_rate {
    type: average
    sql: ${TABLE}.shot_conversion_rate ;;
    label: "Avg shot conversion rate"
    value_format_name: percent_1
  }

  measure: players_with_5_plus_goals {
    type: count_distinct
    sql: ${player_id} ;;
    filters: [goals: ">=5"]
    label: "Players with 5+ goals"
  }

  measure: players_with_10_plus_goals {
    type: count_distinct
    sql: ${player_id} ;;
    filters: [goals: ">=10"]
    label: "Players with 10+ goals"
  }
}
