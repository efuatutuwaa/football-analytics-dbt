export const CASE_STUDY_NAV = [
  { id: "overview", label: "Overview" },
  { id: "architecture", label: "Architecture" },
  { id: "ingestion", label: "Ingestion" },
  { id: "scale", label: "Scale" },
  { id: "modelling", label: "Modelling" },
  { id: "domain", label: "Domain" },
  { id: "data-quality", label: "Data quality" },
  { id: "consumption", label: "Consumption" },
  { id: "whats-next", label: "What's next" },
] as const;

const HEADING_IDS: Record<string, string> = {
  "01 — Overview": "overview",
  "02 — Architecture": "architecture",
  "03 — Ingestion": "ingestion",
  "04 — Scale": "scale",
  "05 — Modelling": "modelling",
  "06 — Domain Knowledge": "domain",
  "07 — Data Quality": "data-quality",
  "08 — Consumption": "consumption",
  "09 — What's Next": "whats-next",
};

export function headingToId(text: string): string | undefined {
  return HEADING_IDS[text.trim()];
}
