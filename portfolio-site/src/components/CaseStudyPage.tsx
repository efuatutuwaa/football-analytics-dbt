"use client";

import { Button, ButtonGroup } from "./Button";
import { CaseStudyNav } from "./CaseStudyNav";
import { CaseStudyMarkdown } from "./CaseStudyMarkdown";
import { createProseComponents } from "./markdown/proseComponents";
import { LINKS } from "@/data/links";

interface CaseStudyPageProps {
  content: string;
}

export function CaseStudyPage({ content }: CaseStudyPageProps) {
  const components = createProseComponents();

  return (
    <div className="min-h-screen bg-off-white">
      <CaseStudyNav />
      <article className="mx-auto max-w-3xl px-6 py-12 pb-24 md:py-16">
        <p className="mb-10 text-[0.625rem] font-bold uppercase tracking-[0.16em] text-muted">
          Technical appendix
        </p>
        <CaseStudyMarkdown content={content} components={components} />

        <div className="mt-12 border-t border-border pt-10">
          <p className="mb-5 text-[0.625rem] font-bold uppercase tracking-[0.16em] text-muted">
            Explore the project
          </p>
          <ButtonGroup>
            <Button href={LINKS.repository}>View Repository ↗</Button>
            <Button href="/" variant="secondary" external={false}>
              ← Back to the story
            </Button>
          </ButtonGroup>
        </div>
      </article>
    </div>
  );
}
