import type { HiveEvent, HiveTask } from "../types";
import { Panel } from "./ui";

export function WorkerPanel({ events, tasks, className, fill = false }: { events: HiveEvent[]; tasks: HiveTask[]; className?: string; fill?: boolean }) {
  const workers = new Map<string, { task?: string; kind?: string; attempt?: number; fence?: number; since?: number }>();
  events.forEach(e => {
    if (e.kind === "claim") workers.set(e.worker, { task: e.task, kind: e.task_kind, attempt: e.attempt, fence: e.fence, since: e.ts });
  });
  const title = (id?: string) => tasks.find(t => t.id === id)?.title ?? "—";
  const rows = [...workers.entries()];
  return (
    <Panel title="Symbiotes" className={className} fill={fill} meta={<span className="tnum font-mono text-[11px] text-faint">{rows.length} worker{rows.length === 1 ? "" : "s"}</span>} pad={false}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line">
              {["worker", "claimed task", "attempt", "fence"].map(h => (
                <th key={h} className="kicker px-4 py-2.5 text-left font-medium first:pl-5 last:pr-5">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={4} className="px-5 py-6 text-[13px] text-faint">No claims yet — workers appear when Knull's plan is picked up.</td></tr>
            )}
            {rows.map(([w, c]) => (
              <tr key={w} className="border-b border-line/60 last:border-0">
                <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[12px] text-info first:pl-5">{w}</td>
                <td className="px-4 py-2.5">
                  {title(c.task)} <span className="text-faint">({c.kind})</span>
                </td>
                <td className="tnum px-4 py-2.5 font-mono text-[12px] text-muted">{c.attempt}</td>
                <td className="tnum px-4 py-2.5 font-mono text-[12px] text-muted last:pr-5">{c.fence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
