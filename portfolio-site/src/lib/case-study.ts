import fs from "fs";
import path from "path";

const CASE_STUDY_PATH = path.join(
  process.cwd(),
  "..",
  "docs",
  "case-study.md"
);

export function loadCaseStudy(): string {
  return fs.readFileSync(CASE_STUDY_PATH, "utf-8");
}
