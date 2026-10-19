import { useCallback, useEffect, useRef, useState } from "react";
import type { HiveRun, HiveTask } from "./types";

const POLL_MS = 1500;

async function fetchRun(id: string): Promise<HiveRun> {
  const r = await fetch(`/v1/hive/runs/${id}`);
  if (!r.ok) throw new Error(`API ${r.status}`);
  return r.json();
}

export async function launchRun(objective: string, workers: number, budget: number): Promise<string> {
  const r = await fetch(`/v1/hive/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objective, workers, subtasks: Math.min(4, workers + 1), budget_tokens: budget }),
  });
  if (!r.ok) throw new Error(`launch failed: ${r.status}`);
  return (await r.json()).run_id as string;
}

/** Live mode: poll the FastAPI hive endpoints. */
export function useLiveRun(runId: string | null) {
  const [run, setRun] = useState<HiveRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!runId) return;
    let dead = false;
    const tick = async () => {
      try {
        const r = await fetchRun(runId);
        if (!dead) { setRun(r); setError(null); }
      } catch (e: any) { if (!dead) setError(String(e?.message || e)); }
    };
    tick();
    const t = setInterval(() => { if (run?.status === "running" || !run) tick(); else tick(); }, POLL_MS);
    return () => { dead = true; clearInterval(t); };
  }, [runId]);
  return { run, error };
}

/** Demo mode: replay a recorded offline hive run (no API keys, no server). */
export function useDemoRun(active: boolean) {
  const [run, setRun] = useState<HiveRun | null>(null);
  const timers = useRef<number[]>([]);

  const stop = () => { timers.current.forEach(clearTimeout); timers.current = []; };

  const replay = useCallback(async () => {
    stop();
    const full: HiveRun = await (await fetch("/demo-run.json")).json();
    const pendingTasks: HiveTask[] = full.tasks.map(t => ({ ...t, status: "pending", result: null }));
    const base: HiveRun = { ...full, status: "running", report: "", spent_tokens: 0,
      tasks: pendingTasks, facts: [], events: [], usage_by_route: [] };
    setRun({ ...base });

    const claims = full.events.filter(e => e.kind === "claim");
    const stepMs = 1400;
    let at = 800;
    const schedule = (fn: () => void) => { timers.current.push(window.setTimeout(fn, at)); };

    claims.forEach((ev, i) => {
      schedule(() => setRun(prev => {
        if (!prev) return prev;
        const tasks = prev.tasks.map(t => {
          if (t.id === ev.task) return { ...t, status: "claimed" };
          // when a verify task is claimed, its research dep is done; reveal its facts as proposed
          const claimTask = full.tasks.find(x => x.id === ev.task);
          if (claimTask && claimTask.kind === "verify" && claimTask.deps.includes(t.id) && t.status === "claimed") return { ...t, status: "done" };
          if (claimTask && claimTask.kind === "write" && t.kind === "verify" && t.status === "claimed") return { ...t, status: "done" };
          return t;
        });
        const claimTask = full.tasks.find(x => x.id === ev.task);
        let facts = prev.facts;
        if (claimTask?.kind === "verify") {
          const depId = claimTask.deps[0];
          const proposed = full.facts.filter(f => f.task_id === depId);
          facts = dedupe([...prev.facts, ...proposed.map(f => ({ ...f, status: "proposed" }))]);
        }
        if (claimTask?.kind === "write") {
          facts = prev.facts.map(f => ({ ...f, status: full.facts.find(x => x.id === f.id)?.status || f.status }));
        }
        const evts = [...prev.events, ev];
        return { ...prev, tasks, facts, events: evts,
          spent_tokens: Math.round((i + 1) / (claims.length + 1) * full.spent_tokens) };
      }));
      at += stepMs;
    });
    // finalize
    schedule(() => setRun(prev => prev && { ...full, tasks: full.tasks.map(t => ({ ...t })), }));
    at += stepMs * 2;
  }, []);

  useEffect(() => { if (active) { replay(); } return stop; }, [active]);
  return { run, replay };
}

function dedupe(facts: HiveRun["facts"]) {
  const seen = new Set<string>();
  return facts.filter(f => (seen.has(f.id) ? false : (seen.add(f.id), true)));
}
