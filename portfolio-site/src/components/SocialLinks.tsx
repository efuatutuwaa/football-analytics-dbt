"use client";

import { motion } from "framer-motion";
import { GitHubIcon, LinkedInIcon } from "./icons";
import { LINKS } from "@/data/links";

const links = [
  {
    href: LINKS.repository,
    label: "Football Analytics dbt",
    description: "Follow the project on GitHub",
    icon: GitHubIcon,
  },
  {
    href: LINKS.linkedin,
    label: "Efua Tutuwaa-Ampofo",
    description: "Connect on LinkedIn",
    icon: LinkedInIcon,
  },
] as const;

export function SocialLinks() {
  return (
    <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
      {links.map((link, i) => (
        <motion.a
          key={link.href}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: i * 0.08 }}
          whileHover={{ y: -2 }}
          className="group flex items-center gap-3 rounded-full border border-border bg-white/60 px-5 py-3 text-sm font-medium text-charcoal shadow-sm transition-all hover:border-charcoal/20 hover:shadow-[0_8px_24px_rgba(0,0,0,0.06)]"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-charcoal text-off-white transition-colors group-hover:bg-charcoal-soft">
            <link.icon className="h-4 w-4" />
          </span>
          <span>
            <span className="block text-[0.6875rem] font-semibold uppercase tracking-[0.1em] text-muted">
              {link.description}
            </span>
            <span className="block">{link.label}</span>
          </span>
        </motion.a>
      ))}
    </div>
  );
}
