"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

interface InsightCardProps {
  label: string;
  children: ReactNode;
  accent?: "green" | "gold" | "ingest" | "neutral";
}

const accentMap = {
  green: "border-green/40",
  gold: "border-gold/40",
  ingest: "border-[#4a6fa5]/40",
  neutral: "border-border",
};

export function InsightCard({ label, children, accent = "neutral" }: InsightCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-5%" }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={`border-l-2 pl-5 py-1 ${accentMap[accent]}`}
    >
      <p className="mb-2 text-[0.625rem] font-bold uppercase tracking-[0.14em] text-muted">
        {label}
      </p>
      <div className="text-[0.9375rem] leading-relaxed text-[#555]">{children}</div>
    </motion.div>
  );
}

interface StatRowProps {
  stats: readonly { value: string; label: string }[];
}

export function StatRow({ stats }: StatRowProps) {
  return (
    <div className="my-12 flex flex-wrap gap-x-10 gap-y-8 border-y border-border py-10">
      {stats.map((stat) => (
        <div key={stat.label}>
          <div className="font-serif text-[clamp(2.25rem,5vw,3.25rem)] leading-none tracking-[-0.03em] text-charcoal">
            {stat.value}
          </div>
          <div className="mt-2 max-w-[12ch] text-xs text-muted">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}

interface EditorialDividerProps {
  label?: string;
}

export function EditorialDivider({ label }: EditorialDividerProps) {
  return (
    <div className="my-16 flex flex-col items-center gap-3 text-center" aria-hidden="true">
      <div className="h-12 w-px bg-gradient-to-b from-transparent via-border to-transparent" />
      {label && (
        <span className="text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-muted">
          {label}
        </span>
      )}
      <span className="text-muted/60">↓</span>
    </div>
  );
}

interface ChapterLabelProps {
  children: ReactNode;
}

export function ChapterLabel({ children }: ChapterLabelProps) {
  return (
    <p className="mb-4 text-[0.625rem] font-bold uppercase tracking-[0.16em] text-muted">
      {children}
    </p>
  );
}

interface SectionHeadingProps {
  children: ReactNode;
  className?: string;
}

export function SectionHeading({ children, className = "" }: SectionHeadingProps) {
  return (
    <h2
      className={`font-serif text-[clamp(2rem,5vw,3.25rem)] leading-[1.08] tracking-[-0.02em] text-charcoal ${className}`}
    >
      {children}
    </h2>
  );
}
