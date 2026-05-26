connection: "databricks"

include: "/views/**/*.view.lkml"

# Set in Looker Admin → Constants (or replace literals in view sql_table_name).
# Example: catalog = main, schema = football_marts
constant: football_catalog {
  value: "main"
}

constant: football_marts_schema {
  value: "football_marts"
}

explore: mart_club_season {
  label: "Club season (domestic league)"
  description: "One row per club per domestic league per season. Big-five leagues."
  group_label: "Football marts"
}

explore: mart_player_season {
  label: "Player season"
  description: "One row per player per club per league per season. Goals, assists, per-90, shots, cards, rating. Mid-season transfers = multiple rows."
  group_label: "Football marts"
}

explore: mart_transfer_window {
  label: "Transfer window (fee moves)"
  description: "Fee-bearing permanent transfers. transfer_fee is raw API text — use mart_player_value_changes for EUR."
  group_label: "Football marts"
}

explore: mart_player_value_changes {
  label: "Transfer fee changes"
  description: "Fee moves with EUR parsing and delta vs the player's prior fee-bearing transfer."
  group_label: "Football marts"
}

explore: mart_league_standings {
  label: "League standings (snapshot)"
  description: "Latest domestic table per big-five league season. Point-in-time API snapshot."
  group_label: "Football marts"
}

explore: mart_national_team_honours {
  label: "National team honours (podium)"
  description: "WC and Euros Winner, Runner-up, Semi-finalist. Join dim_national_team, not dim_club."
  group_label: "Football marts"
}

explore: mart_club_honours {
  label: "Club honours (trophies)"
  description: "Trophy counts per club season — league, domestic cups, UCL/CWC. Treble/Double labels."
  group_label: "Football marts"
}

explore: mart_club_european_performance {
  label: "European club performance"
  description: "UCL and Club World Cup campaign summary per club per season — farthest round, group snapshot, winner flag."
  group_label: "Football marts"
}
