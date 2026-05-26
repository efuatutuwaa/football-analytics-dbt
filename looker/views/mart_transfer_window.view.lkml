view: mart_transfer_window {
  sql_table_name: `@{football_catalog}`.`@{football_marts_schema}`.`mart_transfer_window` ;;

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

  dimension: transfer_fee {
    type: string
    sql: ${TABLE}.transfer_fee ;;
    label: "Fee (raw API)"
  }

  dimension: transfer_type {
    type: string
    sql: ${TABLE}.transfer_type ;;
  }

  measure: transfer_count {
    type: count
    label: "Transfers"
  }
}
