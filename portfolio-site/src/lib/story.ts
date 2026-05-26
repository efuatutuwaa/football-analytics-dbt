import fs from "fs";
import path from "path";

export type StorySection = {
  id: string;
  title: string;
  body: string;
};

export type StoryDocument = {
  title: string;
  epigraph: string;
  intro: string;
  sections: StorySection[];
};

const STORY_PATH = path.join(
  process.cwd(),
  "..",
  "docs",
  "football_analytics_story.md"
);

function parseHeading(line: string): { title: string; id: string } | null {
  const match = line.match(/^##\s+(.+?)(?:\s+\{#(.+?)\})?\s*$/);
  if (!match) return null;
  const title = match[1].trim();
  const id =
    match[2]?.trim() ||
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
  return { title, id };
}

export function loadStory(): StoryDocument {
  const raw = fs.readFileSync(STORY_PATH, "utf-8");
  const lines = raw.split("\n");

  let title = "A Data Engineering Journey";
  let epigraph = "";
  const introLines: string[] = [];
  const sections: StorySection[] = [];

  let i = 0;

  if (lines[i]?.startsWith("# ")) {
    title = lines[i].slice(2).trim();
    i++;
  }

  while (i < lines.length && lines[i].trim() === "") i++;

  if (lines[i]?.startsWith("> ")) {
    epigraph = lines[i].slice(2).trim();
    i++;
  }

  while (i < lines.length) {
    const line = lines[i];
    const heading = parseHeading(line);

    if (heading) {
      i++;
      const bodyLines: string[] = [];
      while (i < lines.length && !lines[i].startsWith("## ")) {
        bodyLines.push(lines[i]);
        i++;
      }
      sections.push({
        id: heading.id,
        title: heading.title,
        body: bodyLines.join("\n").trim(),
      });
      continue;
    }

    if (line.trim() === "---") {
      i++;
      continue;
    }

    if (sections.length === 0 && line.trim()) {
      introLines.push(line);
    }

    i++;
  }

  return {
    title,
    epigraph,
    intro: introLines.join("\n").trim(),
    sections,
  };
}

export const NAV_FROM_STORY = [
  { id: "opening", label: "Opening" },
  { id: "idea", label: "Idea" },
  { id: "learn", label: "Learn" },
  { id: "modelling", label: "Modelling" },
  { id: "scaling", label: "Scaling" },
  { id: "spinner", label: "Spinner" },
  { id: "humbled", label: "Humbled" },
  { id: "curiosity", label: "Curiosity" },
  { id: "remains", label: "Remains" },
  { id: "closing", label: "Close" },
] as const;
