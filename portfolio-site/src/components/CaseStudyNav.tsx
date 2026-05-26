"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CASE_STUDY_NAV } from "@/data/case-study-nav";

export function CaseStudyNav() {
  const [active, setActive] = useState<string>(CASE_STUDY_NAV[0].id);

  useEffect(() => {
    const ids = CASE_STUDY_NAV.map((s) => s.id);
    const observers = ids.map((id) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const obs = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setActive(id);
        },
        { rootMargin: "-20% 0px -65% 0px", threshold: 0 }
      );
      obs.observe(el);
      return obs;
    });
    return () => observers.forEach((o) => o?.disconnect());
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-off-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-x-4 gap-y-2 px-6 py-3">
        <Link
          href="/"
          className="mr-1 shrink-0 text-sm font-medium text-charcoal transition-colors hover:text-muted"
        >
          ← Back
        </Link>
        <span className="hidden h-4 w-px bg-border sm:block" aria-hidden="true" />
        <nav
          className="flex flex-1 flex-wrap items-center gap-x-1 gap-y-1"
          aria-label="Case study sections"
        >
          {CASE_STUDY_NAV.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className={`rounded-full px-2.5 py-1 text-[0.6875rem] font-medium transition-colors ${
                active === section.id
                  ? "bg-charcoal text-off-white"
                  : "text-muted hover:bg-black/5 hover:text-charcoal"
              }`}
            >
              {section.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
