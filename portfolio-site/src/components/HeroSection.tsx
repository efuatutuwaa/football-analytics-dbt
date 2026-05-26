"use client";

import { motion, useScroll, useTransform } from "framer-motion";
import { Button, ButtonGroup } from "./Button";
import { StoryIntro } from "./StoryRenderer";
import { LINKS } from "@/data/links";

interface HeroSectionProps {
  title: string;
  epigraph: string;
  intro: string;
}

export function HeroSection({ title, epigraph, intro }: HeroSectionProps) {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 600], [0, 120]);
  const opacity = useTransform(scrollY, [0, 400], [1, 0.3]);

  return (
    <section
      id="opening"
      className="relative flex min-h-screen items-center overflow-hidden bg-charcoal scroll-mt-0"
    >
      <motion.div style={{ y }} className="absolute inset-0" aria-hidden="true">
        <div
          className="absolute inset-0 bg-cover bg-center grayscale"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=1920&q=80&auto=format&fit=crop')",
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-charcoal via-charcoal/85 to-charcoal/60" />
      </motion.div>

      <motion.div
        style={{ opacity }}
        className="relative z-10 mx-auto w-full max-w-3xl px-6 py-32 pt-40"
      >
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="mb-8 text-[0.625rem] font-semibold uppercase tracking-[0.16em] text-white/40"
        >
          Analytics engineering portfolio · May 2026
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.35, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-[12ch] font-serif text-[clamp(2.75rem,9vw,5.5rem)] leading-[1.02] tracking-[-0.035em] text-white"
        >
          {title}
        </motion.h1>

        <motion.blockquote
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.55 }}
          className="mt-10 max-w-md border-l border-white/25 pl-5 font-serif text-[clamp(1.25rem,2.5vw,1.625rem)] italic leading-snug text-white/90"
        >
          {epigraph}
        </motion.blockquote>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.75 }}
          className="mt-10 max-w-lg"
        >
          <StoryIntro intro={intro} />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.95 }}
        >
          <ButtonGroup className="mt-12">
            <Button href={LINKS.repository}>View Repository</Button>
            <Button href="/case-study" variant="outline-light" external={false}>
              Read Technical Case Study
            </Button>
            <Button href="/gallery" variant="outline-light" external={false}>
              View Gallery ↗
            </Button>
          </ButtonGroup>
        </motion.div>
      </motion.div>
    </section>
  );
}
