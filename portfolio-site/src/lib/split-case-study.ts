const SCALE_SECTION_START = "## 04 — Scale";
const SCALE_SECTION_END = "## 05 — Modelling";

export type CaseStudyContentParts = {
  before: string;
  after: string;
};

export function splitCaseStudyContent(content: string): CaseStudyContentParts {
  const scaleStart = content.indexOf(SCALE_SECTION_START);
  const scaleEnd = content.indexOf(SCALE_SECTION_END);

  if (scaleStart === -1 || scaleEnd === -1 || scaleEnd <= scaleStart) {
    return { before: content, after: "" };
  }

  return {
    before: content.slice(0, scaleStart).trimEnd(),
    after: content.slice(scaleEnd).trimStart(),
  };
}
