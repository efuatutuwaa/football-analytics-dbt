"use client";

import { ReactNode } from "react";
import type { Components } from "react-markdown";
import { headingToId } from "@/data/case-study-nav";

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

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function createProseComponents(): Components {
  return {
    h1: ({ children }) => (
      <h1 className="mb-8 font-serif text-[clamp(2.25rem,5vw,3.25rem)] leading-[1.08] tracking-[-0.02em] text-charcoal">
        {children}
      </h1>
    ),
    h2: ({ children }) => {
      const text = getTextContent(children);
      const id = headingToId(text) ?? slugify(text.replace(/^\d+\s*[—–-]\s*/, ""));

      return (
        <h2
          id={id}
          className="scroll-mt-28 mb-6 mt-16 border-t border-border pt-12 font-serif text-[clamp(1.5rem,4vw,2.25rem)] leading-[1.12] tracking-[-0.02em] text-charcoal first:mt-0 first:border-t-0 first:pt-0"
        >
          {children}
        </h2>
      );
    },
    h3: ({ children }) => (
      <h3 className="mb-4 mt-10 text-base font-semibold tracking-[-0.01em] text-charcoal">
        {children}
      </h3>
    ),
    p: ({ children }) => (
      <p className="mb-5 text-[0.9375rem] leading-[1.75] text-[#555]">{children}</p>
    ),
    blockquote: ({ children }) => (
      <blockquote className="my-8 border-l-2 border-charcoal py-1 pl-6 font-serif text-lg italic leading-relaxed text-charcoal md:text-xl">
        {children}
      </blockquote>
    ),
    hr: () => (
      <hr className="my-12 border-0 bg-gradient-to-r from-transparent via-border to-transparent h-px" />
    ),
    ul: ({ children }) => (
      <ul className="mb-6 list-none space-y-2 pl-0 text-[0.9375rem] text-[#555]">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="mb-6 list-decimal space-y-2 pl-5 text-[0.9375rem] text-[#555]">{children}</ol>
    ),
    li: ({ children }) => (
      <li className="leading-relaxed [&>ul]:mt-2 [&>ol]:mt-2">{children}</li>
    ),
    a: ({ href, children }) => (
      <a
        href={href}
        className="font-medium text-charcoal underline decoration-border underline-offset-[3px] transition-colors hover:decoration-charcoal"
        target={href?.startsWith("http") ? "_blank" : undefined}
        rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
      >
        {children}
      </a>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-charcoal">{children}</strong>
    ),
    em: ({ children }) => <em className="italic text-[#555]">{children}</em>,
    code: ({ className, children }) => {
      const isBlock = className?.includes("language-");

      if (isBlock) {
        return (
          <code className="block bg-transparent p-0 font-mono text-[0.8125rem] leading-relaxed text-charcoal">
            {children}
          </code>
        );
      }

      return (
        <code className="rounded border border-border/70 bg-warm px-1.5 py-0.5 font-mono text-[0.85em] text-charcoal">
          {children}
        </code>
      );
    },
    pre: ({ children }) => (
      <pre className="my-6 overflow-x-auto rounded-lg border border-border bg-warm px-4 py-3.5 font-mono text-[0.8125rem] leading-relaxed text-charcoal shadow-sm">
        {children}
      </pre>
    ),
    table: ({ children }) => (
      <div className="my-8 overflow-x-auto rounded-lg border border-border">
        <table className="w-full min-w-[28rem] border-collapse text-sm">{children}</table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="border-b border-border bg-warm/80">{children}</thead>
    ),
    tbody: ({ children }) => <tbody className="divide-y divide-border/70">{children}</tbody>,
    tr: ({ children }) => <tr className="transition-colors hover:bg-warm/30">{children}</tr>,
    th: ({ children }) => (
      <th className="px-4 py-3 text-left text-[0.6875rem] font-bold uppercase tracking-[0.08em] text-muted">
        {children}
      </th>
    ),
    td: ({ children }) => (
      <td className="px-4 py-3 text-[0.875rem] leading-relaxed text-[#555]">{children}</td>
    ),
  };
}
