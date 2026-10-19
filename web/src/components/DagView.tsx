import type { HiveEvent, HiveTask } from "../types";
import { Panel } from "./ui";

const COL_X: Record<string, number> = { knull: 24, research: 268, verify: 512, write: 756 };
const NODE_W = 196, NODE_H = 54, GAP_Y = 70, PAD_Y = 22;

const STATUS_COLOR: Record<string, string> = {
  pending: "var(--color-faint)",
  claimed: "var(--color-info)",
  done: "var(--color-ok)",
  exhausted: "var(--color-bad)",
  failed: "var(--color-bad)",
};

interface Placed { task: HiveTask; x: number; y: number }

export function DagView({ tasks, events }: { tasks: HiveTask[]; events: HiveEvent[] }) {
  const claimedBy = new Map<string, string>();
  events.forEach(e => { if (e.kind === "claim") claimedBy.set(e.task, e.worker); });

  const byKind = (k: string) => tasks.filter(t => t.kind === k);
  const placed: Placed[] = [];
  const knullY = PAD_Y + (Math.max(1, byKind("research").length) - 1) * GAP_Y / 2;
  placed.push({ task: { id: "knull", kind: "knull", title: "Knull · planner", status: "done", attempt: 1, deps: [] }, x: COL_X.knull, y: knullY });
  byKind("research").forEach((t, i) => placed.push({ task: t, x: COL_X.research, y: PAD_Y + i * GAP_Y }));
  byKind("verify").forEach((t, i) => placed.push({ task: t, x: COL_X.verify, y: PAD_Y + i * GAP_Y }));
  byKind("write").forEach(t => placed.push({ task: t, x: COL_X.write, y: knullY }));

  const pos = new Map(placed.map(p => [p.task.id, p]));
  const edges: [string, string][] = [];
  byKind("research").forEach(t => edges.push(["knull", t.id]));
  tasks.forEach(t => t.deps.forEach(d => edges.push([d, t.id])));

  const height = Math.max(...placed.map(p => p.y)) + NODE_H + PAD_Y;
  const width = COL_X.write + NODE_W + 28;

  const legend: [string, string][] = [
    ["pending", "pending"], ["claimed", "claimed"], ["done", "done"], ["exhausted", "exhausted"],
  ];

  return (
    <Panel
      title="Task graph"
      meta={
        <div className="flex flex-wrap items-center gap-x-3.5 gap-y-1">
          {legend.map(([st, label]) => (
            <span key={st} className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
              <span className="size-1.5 rounded-full" style={{ background: STATUS_COLOR[st] }} />
              {label}
            </span>
          ))}
        </div>
      }
      pad={false}
    >
      <div className="overflow-x-auto max-md:[mask-image:linear-gradient(to_right,black_85%,transparent_98%)]">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto w-full min-w-[560px]"
          role="img"
          aria-label="hive task graph"
        >
          <defs>
            <pattern id="dag-dots" width="22" height="22" patternUnits="userSpaceOnUse">
              <circle cx="1.2" cy="1.2" r="1.2" fill="var(--color-line)" />
            </pattern>
            {(["edge-idle", "edge-live", "edge-done"] as const).map(id => (
              <marker key={id} id={id} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto">
                <path d="M0,0.6 L7.4,4 L0,7.4 z" fill={
                  id === "edge-live" ? "var(--color-info)" :
                  id === "edge-done" ? "var(--color-line-strong)" : "var(--color-line-strong)"
                } />
              </marker>
            ))}
          </defs>

          <rect x="0" y="0" width={width} height={height} fill="url(#dag-dots)" opacity="0.5" />

          {edges.map(([a, b]) => {
            const pa = pos.get(a), pb = pos.get(b);
            if (!pa || !pb) return null;
            const x1 = pa.x + NODE_W, y1 = pa.y + NODE_H / 2, x2 = pb.x, y2 = pb.y + NODE_H / 2;
            const liveEdge = pb.task.status === "claimed";
            const doneEdge = pb.task.status === "done";
            return (
              <path
                key={a + b}
                d={`M${x1},${y1} C${x1 + 26},${y1} ${x2 - 26},${y2} ${x2},${y2}`}
                fill="none"
                stroke={liveEdge ? "var(--color-info)" : "var(--color-line-strong)"}
                strokeWidth={liveEdge ? 1.6 : 1.2}
                strokeOpacity={doneEdge && !liveEdge ? 0.55 : 1}
                className={liveEdge ? "edge-live" : undefined}
                markerEnd={`url(#${liveEdge ? "edge-live" : doneEdge ? "edge-done" : "edge-idle"})`}
              />
            );
          })}

          {placed.map(p => {
            const st = p.task.status;
            const isKnull = p.task.kind === "knull";
            const claimed = st === "claimed";
            const worker = claimedBy.get(p.task.id);
            return (
              <g key={p.task.id}>
                <rect
                  x={p.x} y={p.y} width={NODE_W} height={NODE_H} rx={8}
                  fill="var(--color-raised)"
                  stroke={claimed ? "var(--color-info)" : "var(--color-line-strong)"}
                  strokeWidth={claimed ? 1.4 : 1}
                  style={claimed ? { filter: "drop-shadow(0 0 10px rgba(94,168,255,0.18))" } : undefined}
                />
                <circle
                  cx={p.x + NODE_W - 14} cy={p.y + 14} r={3.25}
                  fill={STATUS_COLOR[st] ?? "var(--color-faint)"}
                  className={claimed ? "dot-live" : undefined}
                />
                <text
                  x={p.x + 13} y={p.y + 19}
                  fill={isKnull ? "var(--color-accent)" : "var(--color-faint)"}
                  fontFamily="var(--font-mono)" fontSize="9.5" letterSpacing="1.4"
                  style={{ textTransform: "uppercase" }}
                >
                  {(isKnull ? "◆ " : "") + p.task.kind.toUpperCase()}{p.task.attempt > 1 ? ` · TRY ${p.task.attempt}` : ""}
                </text>
                {worker && claimed && (
                  <text
                    x={p.x + NODE_W - 26} y={p.y + 19} textAnchor="end"
                    fill="var(--color-info)" fontFamily="var(--font-mono)" fontSize="9.5" letterSpacing="0.6"
                  >
                    {worker}
                  </text>
                )}
                {titleLines(p.task.title).map((line, i, arr) => (
                  <text key={i} x={p.x + 13} y={p.y + (arr.length > 1 ? 33 + i * 13 : 38)} fill="var(--color-foreground)" fontSize="12">
                    {line}
                  </text>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
    </Panel>
  );
}
function clip(s: string, n: number) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

/* Split a task title into at most two lines that fit the node; ellipsis on overflow. */
function titleLines(title: string): string[] {
  if (title.length <= 27) return [title];
  const words = title.split(" ");
  const lines: string[] = [];
  let cur = "";
  for (const w of words) {
    const next = cur ? cur + " " + w : w;
    if (next.length <= 24) { cur = next; continue; }
    if (lines.length === 1) return [lines[0], clip(cur + " " + w, 24)];
    lines.push(cur); cur = w;
  }
  if (cur) lines.push(lines.length === 1 ? clip(cur, 24) : cur);
  return lines.slice(0, 2);
}
