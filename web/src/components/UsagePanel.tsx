import type { UsageRow } from "../types";
import { Panel } from "./ui";

export function UsagePanel({ usage, className, fill = false }: { usage: UsageRow[]; className?: string; fill?: boolean }) {
  return (
    <Panel title="Usage by route" className={className} fill={fill} meta={<span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">layer · agent · provider</span>} pad={false}>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-line">
              {["layer", "agent", "provider", "model", "calls", "in", "out"].map(h => (
                <th key={h} className="kicker px-4 py-2.5 text-left font-medium first:pl-5 last:pr-5">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {usage.length === 0 && (
              <tr><td colSpan={7} className="px-5 py-6 text-[13px] text-faint">No LLM calls yet.</td></tr>
            )}
            {usage.map((u, i) => (
              <tr key={i} className="border-b border-line/60 last:border-0">
                <td className="px-4 py-2.5 font-mono text-[12px] text-muted first:pl-5">{u.layer}</td>
                <td className="px-4 py-2.5 font-mono text-[12px]">{u.agent}</td>
                <td className="px-4 py-2.5 text-muted">{u.provider}</td>
                <td className="px-4 py-2.5 font-mono text-[12px] text-muted">{u.model}</td>
                <td className="tnum px-4 py-2.5 font-mono text-[12px]">{u.calls}</td>
                <td className="tnum px-4 py-2.5 font-mono text-[12px] text-muted">{u.in_tok.toLocaleString()}</td>
                <td className="tnum px-4 py-2.5 font-mono text-[12px] text-muted last:pr-5">{u.out_tok.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
