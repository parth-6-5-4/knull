import type { Fact } from "../types";
import { Panel } from "./ui";
import { cn } from "../lib/cn";

export function FactsPanel({ facts }: { facts: Fact[] }) {
  const col = (status: string, label: string, dot: string, count: string) => {
    const rows = facts.filter(f => f.status === status);
    return (
      <Panel
        className="h-full"
        fill
        title={label}
        meta={
          <span className={cn("tnum inline-flex items-center gap-1.5 font-mono text-[11px]", count)}>
            <span className={cn("size-1.5 rounded-full", dot)} />
            {rows.length}
          </span>
        }
      >
        <ul className="flex flex-col gap-4">
          {rows.map(f => (
            <li key={f.id}>
              <div className="text-[13.5px] leading-snug">{f.claim}</div>
              {f.quote && (
                <blockquote className="mt-2 border-l-2 border-line-strong pl-3 text-[12.5px] italic text-muted">
                  “{f.quote}”
                </blockquote>
              )}
              <div className="mt-1.5 font-mono text-[10.5px] tracking-wide text-faint">
                {f.id}{f.note ? ` · ${f.note}` : ""}
              </div>
            </li>
          ))}
          {rows.length === 0 && <li className="text-[13px] text-faint">None yet.</li>}
        </ul>
      </Panel>
    );
  };
  return (
    <div className="grid flex-1 items-stretch gap-4 lg:grid-cols-3">
      {col("verified", "Verified", "bg-ok", "text-ok")}
      {col("proposed", "Proposed", "bg-info", "text-info")}
      {col("rejected", "Rejected", "bg-bad", "text-bad")}
    </div>
  );
}
