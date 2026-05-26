"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

interface PullQuoteProps {
  children: ReactNode;
  lead?: string;
  cite?: string;
  className?: string;
}

export function PullQuote({ children, lead, cite, className = "" }: PullQuoteProps) {
  return (
    <motion.figure
      initial={{ opacity: 0, x: -12 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-10%" }}
      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      className={`my-10 ${className}`}
    >
      {lead && (
        <p className="mb-3 text-[0.9375rem] text-[#555]">{lead}</p>
      )}
      <blockquote className="border-l-2 border-charcoal pl-6 font-serif text-xl italic leading-relaxed text-charcoal md:text-2xl">
        {children}
      </blockquote>
      {cite && (
        <figcaption className="mt-4 pl-6 font-sans text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-muted">
          {cite}
        </figcaption>
      )}
    </motion.figure>
  );
}

interface CinemaBreakProps {
  children: ReactNode;
  cite?: string;
  variant?: "dark" | "light";
}

export function CinemaBreak({ children, cite, variant = "dark" }: CinemaBreakProps) {
  const isDark = variant === "dark";

  return (
    <motion.aside
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-15%" }}
      transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
      className={`relative w-full py-24 md:py-32 px-6 text-center overflow-hidden ${
        isDark ? "bg-charcoal text-off-white" : "bg-warm text-charcoal"
      }`}
    >
      {isDark && (
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          aria-hidden="true"
          style={{
            background:
              "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(74,111,165,0.2) 0%, transparent 60%), radial-gradient(ellipse 40% 40% at 80% 100%, rgba(196,154,108,0.12) 0%, transparent 50%)",
          }}
        />
      )}
      <blockquote className="relative mx-auto max-w-[16ch] font-serif text-[clamp(1.75rem,5vw,3rem)] italic leading-[1.15] tracking-[-0.02em]">
        {children}
      </blockquote>
      {cite && (
        <cite
          className={`relative mt-8 block font-sans text-[0.6875rem] not-italic font-semibold uppercase tracking-[0.14em] ${
            isDark ? "text-white/40" : "text-muted"
          }`}
        >
          {cite}
        </cite>
      )}
    </motion.aside>
  );
}
