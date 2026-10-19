import { Panel } from "./ui";

export function BudgetGauge({ spent, budget }: { spent: number; budget: number }) {
  const pct = Math.min(100, budget > 0 ? (spent / budget) * 100 : 0);
  const hot = pct > 85;
  return (
    <Panel title="Token budget" meta={<span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">hard cap · governor enforced</span>}>
      <div className="h-1.5 overflow-hidden rounded-full bg-raised" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label="token budget used">
        <div
          className="h-full rounded-full transition-[width] duration-500"
          style={{ width: `${pct}%`, background: hot ? "var(--color-bad)" : "var(--color-info)" }}
        />
      </div>
      <div className="tnum mt-2.5 font-mono text-[12px] text-muted">
        {spent.toLocaleString()} / {budget.toLocaleString()} tokens
        <span className={hot ? "text-bad" : "text-faint"}> · {pct.toFixed(1)}%</span>
      </div>
    </Panel>
  );
}
