import type { HiveEvent } from "../types";
import { Panel } from "./ui";
import { cn } from "../lib/cn";

const KIND_TONE: Record<string, string> = {
  plan: "text-accent",
  claim: "text-info",
  watchdog: "text-warn",
  governor: "text-warn",
  publish_rejected: "text-bad",
  task_error: "text-bad",
};

export function EventLog({ events, className, fill = false }: { events: HiveEvent[]; className?: string; fill?: boolean }) {
  return (
    <Panel title="Event stream" className={className} fill={fill} meta={<span className="tnum font-mono text-[11px] text-faint">{events.length} events</span>} pad={false}>
      <ol className={cn("overflow-y-auto px-2 py-2", fill ? "h-full" : "max-h-[300px]")}>
        {[...events].reverse().slice(0, 40).map((e, i) => (
          <li key={i} className="flex items-baseline gap-3 rounded-md px-3 py-1.5 hover:bg-raised">
            <span className={cn(
              "w-[112px] flex-none font-mono text-[10px] uppercase tracking-[0.12em]",
              KIND_TONE[e.kind] ?? "text-faint",
            )}>
              {e.kind.replace(/_/g, " ")}
            </span>
            <span className="min-w-0 text-[12.5px] text-muted">{describe(e)}</span>
          </li>
        ))}
        {events.length === 0 && <li className="px-3 py-6 text-[13px] text-faint">Waiting for the hive…</li>}
      </ol>
    </Panel>
  );
}
function describe(e: HiveEvent): string {
  switch (e.kind) {
    case "plan": return `Knull planned ${e.subtasks?.length ?? 0} subtasks`;
    case "claim": return `${e.worker} claimed ${e.task_kind} (attempt ${e.attempt}, fence ${e.fence})`;
    case "publish_rejected": return `stale publish rejected for ${e.task}`;
    case "task_error": return `${e.worker}: ${e.error}`;
    case "watchdog": return `watchdog: ${e.action ?? "lease sweep"}`;
    case "governor": return `budget governor: ${e.action} (${e.spent}/${e.cap})`;
    default: return JSON.stringify(e).slice(0, 120);
  }
}
