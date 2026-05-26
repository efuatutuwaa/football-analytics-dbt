import { LINKS } from "./links";

export const PLATFORM_STATS = [
  { value: "15", label: "Competitions tracked" },
  { value: "2020→", label: "Seasons ingested" },
  { value: "18", label: "Reporting marts" },
  { value: "75k", label: "API requests / day" },
] as const;

export const STACK_LAYERS = [
  { layer: "Ingestion", tech: "Python + PySpark → Delta", schema: "football_raw" },
  { layer: "Staging", tech: "dbt stg_* views", schema: "football_staging" },
  { layer: "Intermediate", tech: "dbt int_* tables", schema: "football_intermediate" },
  { layer: "Core", tech: "5 dims · 12 facts", schema: "football_core" },
  { layer: "Marts", tech: "18 mart_* models", schema: "football_marts" },
  { layer: "Semantic", tech: "MetricFlow YAML", schema: "football_semantic" },
  { layer: "Consumption", tech: "Streamlit · LookerML", schema: "reads marts + dims" },
] as const;

export const PIPELINE_NODES = [
  {
    phase: "01 · Ingestion",
    title: "Land the data",
    lede: "API-Football becomes typed Delta tables — incremental, quota-aware, ready for modelling.",
    color: "ingest" as const,
    items: [{ name: "Python + PySpark", meta: "football_raw", desc: "19 raw tables · metadata-driven skips" }],
  },
  {
    phase: "02 · Transformation",
    title: "Shape the warehouse",
    lede: "dbt cleans, joins, and encodes business logic. Intermediate models build the star — they never ship to BI.",
    color: "transform" as const,
    items: [
      { name: "Staging", meta: "17 stg_*", desc: "Clean, rename, cast — mostly views" },
      { name: "Intermediate", meta: "14 int_*", desc: "Spines, cup campaigns, transfer periods" },
      { name: "Core", meta: "5 dim · 12 fact", desc: "Star schema contract — football_core" },
    ],
  },
  {
    phase: "03 · Reporting",
    title: "Answer fan questions",
    lede: "Eighteen marts — each with one honest grain.",
    color: "marts" as const,
    items: [{ name: "Marts", meta: "18 mart_*", desc: "League tables, transfers, honours, European campaigns" }],
  },
  {
    phase: "04 · Consumption",
    title: "Prove it works",
    lede: "Apps and semantic definitions people can click — not slides alone.",
    color: "consume" as const,
    items: [
      { name: "Streamlit", meta: "8 pages", desc: "Live on Databricks SQL" },
      { name: "Looker + MetricFlow", meta: "governed", desc: "LookerML and semantic YAML" },
    ],
  },
] as const;

export const EUREKA_MOMENTS = [
  {
    id: "bronze",
    number: "01",
    title: "The bronze layer pattern",
    emotional: "At first, I thought something was broken. It wasn't. The problem was architectural.",
    insight:
      "I was flattening nested JSON during ingestion instead of landing raw payloads first and parsing later. That was the moment I truly understood what flattening-at-ingest costs as the platform scales.",
    closing: "The bronze-layer pattern wasn't the answer for this project — but understanding the trade-off was the real lesson.",
    href: `${LINKS.caseStudy}#02--architecture`,
  },
  {
    id: "scaling",
    number: "02",
    title: "Linear scaling is good news",
    emotional: "The runtime increase looked terrifying until I benchmarked the actual growth.",
    insight:
      "Player rows exploded from around 16,000 to over 41,000 because domestic cups introduced lower-division clubs and entire new squads. The pipeline was scaling linearly.",
    closing: "That was not failure. That was health. Without the original benchmark, I would have spent a day debugging a system that was behaving correctly.",
    href: LINKS.caseStudy,
  },
  {
    id: "league-cup",
    number: "03",
    title: "League ≠ cup",
    emotional: "Nothing would have crashed. The numbers would simply have lied quietly.",
    insight:
      "A Champions League knockout tie is not the same thing as a domestic league fixture. An FA Cup run involving lower-tier clubs changes the meaning of averages and performance comparisons.",
    closing: "Personal fandom is not data domain expertise.",
    quote: true,
    href: `${LINKS.caseStudy}#06--domain-knowledge`,
  },
  {
    id: "humbled",
    number: "04",
    title: "Football data humbled me",
    emotional: "I assumed football would be the easy part because I had watched it my whole life.",
    insight:
      "Transfer histories forced me to think in periods instead of overwritten dimensions. The fix for a twenty-hour transfer fetch was not Spark — it was asking: who actually needs fetching?",
    closing: "That moment stayed with me because it had very little to do with Spark and everything to do with thinking clearly.",
    href: `${LINKS.caseStudy}#03--ingestion`,
  },
  {
    id: "coaches",
    number: "05",
    title: "When the source itself is wrong",
    emotional: "That was the hardest call of the project. Not technically hard. Emotionally hard.",
    insight:
      "The API returned Luis Fuentes as head coach of both France and Spain. Quietly shipping the data and hoping nobody noticed would have been the easiest path. I dropped the entire coaching domain instead.",
    closing: "Bad data shipped quietly is worse than no data at all.",
    quote: true,
    href: `${LINKS.adrs}/009-drop-coach-models-source-data-quality-failure.md`,
  },
] as const;

export const DASHBOARD_SCREENS = [
  {
    id: "league-tables",
    title: "League tables",
    caption: "Club season performance — one grain per league table row.",
    placeholder: "League table screenshot",
  },
  {
    id: "transfers",
    title: "Transfer analysis",
    caption: "Permanent fee moves in EUR — period-based club stints.",
    placeholder: "Transfer analysis screenshot",
  },
  {
    id: "top-scorers",
    title: "Top scorers",
    caption: "Player season stats separated by competition type.",
    placeholder: "Top scorers screenshot",
  },
  {
    id: "european",
    title: "European campaigns",
    caption: "UEFA round labels normalised for honest knockout reporting.",
    placeholder: "European campaigns screenshot",
  },
  {
    id: "squad-value",
    title: "Squad valuation",
    caption: "Club squad value aggregated from market value periods.",
    placeholder: "Squad valuation screenshot",
  },
  {
    id: "ops",
    title: "Operational health",
    caption: "Pipeline health and API usage — football_ops marts.",
    placeholder: "Ops dashboard screenshot",
  },
] as const;
