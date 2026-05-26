view: mart_player_value_changes {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_player_value_changes` ;;

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

  dimension: player_name {
    type: string
    sql: ${TABLE}.player_name ;;
    label: "Player"
  }

  dimension: team_name {
    type: string
    sql: ${TABLE}.team_name ;;
    label: "Destination club"
  }

  dimension: previous_team_name {
    type: string
    sql: ${TABLE}.previous_team_name ;;
    label: "Previous club"
  }

  dimension: transfer_date {
    type: date
    sql: ${TABLE}.transfer_date ;;
  }

  dimension: transfer_year {
    type: number
    sql: ${TABLE}.transfer_year ;;
  }

  dimension: transfer_window {
    type: string
    sql: ${TABLE}.transfer_window ;;
    label: "Window"
  }

  dimension: is_fee_increase {
    type: yesno
    sql: ${TABLE}.is_fee_increase ;;
    label: "Fee increase"
  }

  dimension: is_fee_decrease {
    type: yesno
    sql: ${TABLE}.is_fee_decrease ;;
    label: "Fee decrease"
  }

  dimension: is_first_fee_move {
    type: yesno
    sql: ${TABLE}.is_first_fee_move ;;
    label: "First fee move"
  }

  measure: total_signing_fee_eur {
    type: sum
    sql: ${TABLE}.transfer_fee_eur ;;
    label: "Signing fee (EUR)"
    value_format_name: decimal_0
  }

  measure: total_fee_change_eur {
    type: sum
    sql: ${TABLE}.fee_change_eur ;;
    label: "Fee change (EUR)"
    value_format_name: decimal_0
  }

  measure: avg_fee_change_pct {
    type: average
    sql: ${TABLE}.fee_change_pct ;;
    label: "Avg fee change %"
    value_format_name: decimal_1
  }

  measure: fee_move_count {
    type: count
    label: "Fee moves"
  }
}
