"use client";

import React, { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SectionReveal } from "./SectionReveal";
import { SocialLinks } from "./SocialLinks";
import { CinemaBreak } from "./PullQuote";

const CINEMA_QUOTES = [
  "personal fandom is not domain expertise.",
  "The platform is the artefact.",
  "systems become fast when the question becomes precise.",
  "benchmarks are not just numbers — they are context.",
  "permission to go deep on something you already love.",
];

function getTextContent(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(getTextContent).join("");
  if (node && typeof node === "object" && "props" in node) {
    const el = node as React.ReactElement<{ children?: ReactNode }>;
    return getTextContent(el.props.children);
  }
  return "";
}

function isCinemaQuote(text: string) {
  const normalized = text.replace(/^["']|["']$/g, "").trim().toLowerCase();
  return CINEMA_QUOTES.some((q) => normalized.includes(q.replace(/\.$/, "").toLowerCase()));
}

interface StorySectionBlockProps {
  id: string;
  title: string;
  body: string;
  index: number;
  isClosing?: boolean;
}

export function StorySectionBlock({
  id,
  title,
  body,
  index,
  isClosing = false,
}: StorySectionBlockProps) {
  const bg =
    index % 4 === 1
      ? "bg-warm/40"
      : index % 4 === 3
        ? "bg-green-soft/30"
        : "";

  return (
    <section id={id} className={`scroll-mt-24 py-20 md:py-28 ${bg}`}>
      <div className="mx-auto max-w-3xl px-6">
        <SectionReveal>
          <p className="mb-4 text-[0.625rem] font-bold uppercase tracking-[0.16em] text-muted">
            {String(index + 1).padStart(2, "0")}
          </p>
          <h2 className="font-serif text-[clamp(1.75rem,4.5vw,2.75rem)] leading-[1.1] tracking-[-0.02em] text-charcoal">
            {title}
          </h2>
          <div className="story-prose mt-8 overflow-x-hidden">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => (
                  <p className="mb-5 text-[0.9375rem] leading-[1.75] text-[#555]">{children}</p>
                ),
                ul: ({ children }) => (
                  <ul className="mb-5 list-none space-y-2 pl-0 text-[0.9375rem] text-[#555]">
                    {children}
                  </ul>
                ),
                li: ({ children }) => (
                  <li className="flex gap-3 border-b border-border/50 py-2 last:border-0">
                    <span className="text-muted">·</span>
                    <span>{children}</span>
                  </li>
                ),
                blockquote: ({ children }) => {
                  const text = getTextContent(children).trim();

                  if (isCinemaQuote(text)) {
                    return (
                      <div className="relative left-1/2 my-12 w-screen max-w-none -translate-x-1/2">
                        <CinemaBreak variant={index % 2 === 0 ? "dark" : "light"}>
                          {text.replace(/^["']|["']$/g, "")}
                        </CinemaBreak>
                      </div>
                    );
                  }

                  return (
                    <blockquote className="my-8 border-l-2 border-charcoal py-1 pl-6 font-serif text-xl italic leading-relaxed text-charcoal md:text-2xl">
                      {children}
                    </blockquote>
                  );
                },
                em: ({ children }) => (
                  <em className="font-serif italic text-charcoal">{children}</em>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-charcoal">{children}</strong>
                ),
              }}
            >
              {body}
            </ReactMarkdown>
          </div>
          {isClosing && <SocialLinks />}
        </SectionReveal>
      </div>
    </section>
  );
}

interface StoryIntroProps {
  intro: string;
}

export function StoryIntro({ intro }: StoryIntroProps) {
  return (
    <div className="story-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p className="mb-5 text-[0.9375rem] leading-[1.8] text-white/65">{children}</p>
          ),
        }}
      >
        {intro}
      </ReactMarkdown>
    </div>
  );
}
