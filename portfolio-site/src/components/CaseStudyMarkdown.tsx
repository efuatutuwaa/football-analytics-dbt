"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import { ScaleSectionChart } from "./ScaleSectionChart";
import { splitCaseStudyContent } from "@/lib/split-case-study";

interface CaseStudyMarkdownProps {
  content: string;
  components: Components;
}

function MarkdownBlock({
  content,
  components,
}: {
  content: string;
  components: Components;
}) {
  if (!content.trim()) {
    return null;
  }

  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {content}
    </ReactMarkdown>
  );
}

export function CaseStudyMarkdown({ content, components }: CaseStudyMarkdownProps) {
  const { before, after } = splitCaseStudyContent(content);

  if (!after && before === content) {
    return <MarkdownBlock content={content} components={components} />;
  }

  return (
    <>
      <MarkdownBlock content={before} components={components} />
      <ScaleSectionChart />
      <MarkdownBlock content={after} components={components} />
    </>
  );
}
