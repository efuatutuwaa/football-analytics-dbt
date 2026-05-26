import type { Metadata } from "next";
import { CaseStudyPage } from "@/components/CaseStudyPage";
import { loadCaseStudy } from "@/lib/case-study";

export const metadata: Metadata = {
  title: "Technical Case Study · Football Analytics Platform",
  description:
    "Architecture, ingestion, modelling, and tradeoffs for a production-style football analytics platform built with Python, PySpark, dbt, and Databricks.",
};

export default function CaseStudyRoute() {
  const content = loadCaseStudy();

  return <CaseStudyPage content={content} />;
}
