"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { useEffect, useState } from "react";
import { NAV_SECTIONS, LINKS } from "@/data/links";
import { Button } from "./Button";

export function Navigation() {
  const [active, setActive] = useState("opening");
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();
  const navOpacity = useTransform(scrollY, [0, 120], [0.78, 0.95]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const ids = NAV_SECTIONS.map((s) => s.id);
    const observers = ids.map((id) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const obs = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) setActive(id);
        },
        { rootMargin: "-35% 0px -55% 0px", threshold: 0 }
      );
      obs.observe(el);
      return obs;
    });
    return () => observers.forEach((o) => o?.disconnect());
  }, []);

  return (
    <>
      <motion.header
        style={{ opacity: navOpacity }}
        className={`fixed top-4 left-1/2 z-[100] flex max-w-[calc(100vw-2rem)] -translate-x-1/2 items-center gap-2 rounded-full border border-black/[0.06] bg-white/80 px-2 py-1.5 pl-4 shadow-[0_4px_24px_rgba(0,0,0,0.06)] backdrop-blur-xl transition-all duration-500 ${
          scrolled ? "top-3 shadow-[0_8px_32px_rgba(0,0,0,0.08)]" : ""
        }`}
      >
        <a
          href="#opening"
          className="mr-1 whitespace-nowrap text-xs font-semibold tracking-[-0.02em] text-charcoal"
        >
          Journey
        </a>
        <nav className="hidden items-center gap-0.5 md:flex" aria-label="Sections">
          {NAV_SECTIONS.slice(1, 9).map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={`rounded-full px-2.5 py-1.5 text-[0.6875rem] font-medium transition-colors ${
                active === s.id ? "bg-black/5 text-charcoal" : "text-muted hover:text-charcoal"
              }`}
            >
              {s.label}
            </a>
          ))}
        </nav>
        <a
          href="/gallery"
          className="rounded-full px-2.5 py-1.5 text-[0.6875rem] font-medium text-muted transition-colors hover:text-charcoal"
        >
          Gallery
        </a>
        <Button href={LINKS.repository} className="!px-4 !py-2 !text-xs">
          View Repository
        </Button>
      </motion.header>

      <nav
        className="fixed right-6 top-1/2 z-[90] hidden -translate-y-1/2 flex-col items-end gap-3 xl:flex"
        aria-label="Section progress"
      >
        {NAV_SECTIONS.map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className={`group flex items-center gap-2 transition-opacity ${
              active === s.id ? "opacity-100" : "opacity-30 hover:opacity-70"
            }`}
          >
            <span
              className={`text-[0.625rem] font-semibold uppercase tracking-[0.06em] text-muted transition-all ${
                active === s.id
                  ? "opacity-100 translate-x-0"
                  : "opacity-0 translate-x-1 group-hover:opacity-100 group-hover:translate-x-0"
              }`}
            >
              {s.label}
            </span>
            <span
              className={`h-[5px] w-[5px] rounded-full transition-transform ${
                active === s.id ? "scale-150 bg-charcoal" : "bg-muted-light"
              }`}
            />
          </a>
        ))}
      </nav>
    </>
  );
}
