import { useState } from "react";
import { Play } from "lucide-react";
import { Panel } from "./ui";

export function LaunchForm({ disabled, onLaunch }: { disabled: boolean; onLaunch: (o: string, w: number, b: number) => Promise<void> }) {
  const [objective, setObjective] = useState("Memory architectures for long-horizon LLM agents");
  const [workers, setWorkers] = useState(3);
  const [budget, setBudget] = useState(200000);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const inputCls =
    "w-full rounded-md border border-line-strong bg-ink px-3 py-2 text-[13.5px] text-foreground " +
    "placeholder:text-faint transition-colors hover:border-line-strong focus:border-info focus:outline-none";

  return (
    <Panel title="New hive run" meta={<span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">knull plans · symbiotes execute</span>}>
      <form
        className="flex flex-col gap-4"
        onSubmit={async e => {
          e.preventDefault();
          setBusy(true); setErr(null);
          try { await onLaunch(objective, workers, budget); } catch (x: any) { setErr(String(x?.message || x)); }
          setBusy(false);
        }}
      >
        <label className="flex flex-col gap-1.5">
          <span className="kicker">objective</span>
          <input className={inputCls} value={objective} onChange={e => setObjective(e.target.value)} minLength={5} required />
        </label>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex w-28 flex-col gap-1.5">
            <span className="kicker">workers</span>
            <input className={inputCls} type="number" min={1} max={8} value={workers} onChange={e => setWorkers(+e.target.value)} />
          </label>
          <label className="flex w-40 flex-col gap-1.5">
            <span className="kicker">token budget</span>
            <input className={inputCls} type="number" min={1000} step={1000} value={budget} onChange={e => setBudget(+e.target.value)} />
          </label>
          <button
            type="submit"
            disabled={busy || disabled}
            className="inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-accent-bright active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-accent-dim"
          >
            <Play className="size-3.5" strokeWidth={2.25} />
            {busy ? "Launching…" : "Launch hive"}
          </button>
        </div>
        {err && <p className="text-[13px] text-bad">{err}</p>}
      </form>
    </Panel>
  );
}
