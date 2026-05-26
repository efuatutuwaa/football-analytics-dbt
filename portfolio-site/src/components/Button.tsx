"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "outline-light";

const styles: Record<Variant, string> = {
  primary:
    "bg-charcoal text-off-white hover:bg-charcoal-soft shadow-sm hover:shadow-[0_0_24px_rgba(26,26,26,0.15)]",
  secondary:
    "bg-transparent text-charcoal border border-border hover:border-charcoal/30 hover:bg-white/60",
  ghost: "bg-transparent text-muted hover:text-charcoal underline-offset-4 hover:underline px-0",
  "outline-light":
    "bg-transparent text-white/85 border border-white/25 hover:border-white/50 hover:bg-white/10",
};

interface ButtonProps {
  href: string;
  children: ReactNode;
  variant?: Variant;
  external?: boolean;
  className?: string;
}

export function Button({
  href,
  children,
  variant = "primary",
  external = true,
  className = "",
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-all duration-300 ease-out";

  const content = (
    <motion.span
      whileHover={{ y: variant === "ghost" ? 0 : -1 }}
      whileTap={{ scale: 0.98 }}
      className={`${base} ${styles[variant]} ${className}`}
    >
      {children}
    </motion.span>
  );

  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer">
        {content}
      </a>
    );
  }

  return <Link href={href}>{content}</Link>;
}

interface ButtonGroupProps {
  children: ReactNode;
  className?: string;
}

export function ButtonGroup({ children, className = "" }: ButtonGroupProps) {
  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>{children}</div>
  );
}
