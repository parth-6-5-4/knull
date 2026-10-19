import type { ReactNode } from "react";
import { Hexagon } from "lucide-react";
import { cn } from "../lib/cn";
import { GlowingEffect } from "./ui/glowing-effect";
import { Meteors } from "./ui/meteors";

/* Panel — the one surface container used everywhere. */
export function Panel({ title, meta, children, className, pad = true, fill = false }: {
  title: string; meta?: ReactNode; children: ReactNode; className?: string; pad?: boolean; fill?: boolean;
}) {
  return (
    <section className={cn("relative rounded-2xl border border-line bg-surface shadow-[0_14px_44px_rgba(0,0,0,0.42)]", fill && "flex flex-col", className)}>
      <GlowingEffect variant="white" spread={46} proximity={64} borderWidth={1.5} movementDuration={0.9} disabled={false} />
      <header className="flex flex-none flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-line px-4 py-3 sm:px-5">
        <h2 className="kicker">{title}</h2>
        {meta && <div className="flex items-center gap-3">{meta}</div>}
      </header>
      <div className={cn(pad && "p-4 sm:p-5", fill && "flex min-h-0 flex-1 flex-col")}>{children}</div>
    </section>
  );
}

/* StatusBadge — dot + mono label. Color carries meaning, dot shape stays constant. */
const TONES = {
  neutral: "text-muted border-line-strong",
  info: "text-info border-info/40",
  ok: "text-ok border-ok/40",
  warn: "text-warn border-warn/40",
  bad: "text-bad border-bad/40",
  accent: "text-accent border-accent/40",
} as const;
const DOTS = {
  neutral: "bg-faint",
  info: "bg-info",
  ok: "bg-ok",
  warn: "bg-warn",
  bad: "bg-bad",
  accent: "bg-accent",
} as const;
export type Tone = keyof typeof TONES;

export function StatusBadge({ tone = "neutral", live = false, children }: {
  tone?: Tone; live?: boolean; children: ReactNode;
}) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5",
      "font-mono text-[10.5px] uppercase tracking-[0.12em]",
      TONES[tone],
    )}>
      <span className={cn("size-1.5 rounded-full", DOTS[tone], live && "dot-live")} />
      {children}
    </span>
  );
}

/* StatCard — overview metric. */
export function StatCard({ label, value, tone, className }: {
  label: string; value: ReactNode; tone?: Tone; className?: string;
}) {
  const valueTone =
    tone === "ok" ? "text-ok" : tone === "bad" ? "text-bad" :
    tone === "info" ? "text-info" : tone === "accent" ? "text-accent" : "text-foreground";
  return (
    <div className={cn("relative rounded-2xl border border-line bg-surface px-4 py-3.5 shadow-[0_14px_44px_rgba(0,0,0,0.42)]", className)}>
      <GlowingEffect variant="white" spread={26} proximity={48} borderWidth={1.5} movementDuration={0.7} disabled={false} />
      <div className="kicker">{label}</div>
      <div className={cn("tnum mt-1.5 text-[17px] font-semibold leading-snug", valueTone)}>{value}</div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex flex-col items-center gap-3 overflow-hidden rounded-2xl border border-dashed border-line-strong px-6 py-16 text-center">
      <Meteors number={10} className="opacity-70" />
      <Hexagon className="size-7 text-accent-dim" strokeWidth={1.5} />
      <p className="max-w-md text-[13px] text-faint">{children}</p>
    </div>
  );
}

/* Run status → tone mapping, shared by topbar and views. */
export function runTone(status: string): { tone: Tone; live: boolean } {
  if (status === "running") return { tone: "info", live: true };
  if (status === "done" || status === "done_with_removals") return { tone: "ok", live: false };
  if (status === "stopped" || status === "blocked" || status === "failed") return { tone: "bad", live: false };
  return { tone: "neutral", live: false };
}
