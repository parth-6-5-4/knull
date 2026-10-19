"use client";

/* Adapted from Aceternity UI's resizable-navbar (ui.aceternity.com/components/resizable-navbar),
   driven by the console's own scroll container instead of the window, and
   retinted to the token system: on scroll the full-width bar collapses into a
   floating pill island. */
import { cn } from "@/lib/utils";
import { motion, useScroll, useMotionValueEvent } from "motion/react";
import React, { useState } from "react";

export function CollapsibleNavbar({
  containerRef,
  children,
  className,
}: {
  containerRef: React.RefObject<HTMLElement | null>;
  children: React.ReactNode;
  className?: string;
}) {
  const { scrollY } = useScroll({ container: containerRef });
  const [collapsed, setCollapsed] = useState(false);

  useMotionValueEvent(scrollY, "change", (latest) => {
    setCollapsed(latest > 24);
  });

  return (
    <div className="relative z-40 flex-none self-stretch">
      <motion.header
        initial={false}
        animate={{
          width: collapsed ? "min(860px, calc(100% - 1.5rem))" : "100%",
          y: collapsed ? 8 : 0,
          borderRadius: collapsed ? 16 : 0,
        }}
        transition={{ type: "spring", stiffness: 260, damping: 32 }}
        className={cn(
          "mx-auto flex h-14 items-center justify-between gap-3 px-4 transition-colors duration-300 sm:px-5",
          collapsed
            ? "border border-line bg-surface/85 shadow-lg shadow-black/40 backdrop-blur-md"
            : "border-b border-line bg-ink",
          className,
        )}
      >
        {children}
      </motion.header>
    </div>
  );
}
