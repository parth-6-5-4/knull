import { useMemo, useRef, useState } from "react";
import { Hexagon, LayoutGrid, Workflow, Database, Gauge, FileText } from "lucide-react";
import type { HiveRun } from "./types";
import { useDemoRun, useLiveRun, launchRun } from "./data";
import { DagView } from "./components/DagView";
import { WorkerPanel } from "./components/WorkerPanel";
import { EventLog } from "./components/EventLog";
import { FactsPanel } from "./components/FactsPanel";
import { UsagePanel } from "./components/UsagePanel";
import { ReportView } from "./components/ReportView";
import { LaunchForm } from "./components/LaunchForm";
import { BudgetGauge } from "./components/BudgetGauge";
import { StatCard, StatusBadge, EmptyState, runTone } from "./components/ui";
import { cn } from "./lib/cn";
import { EncryptedText } from "./components/ui/encrypted-text";
import { useReducedMotion } from "motion/react";
import { Sidebar, SidebarBody, SidebarLink, SidebarToggle, useSidebar } from "./components/ui/sidebar";
import { CollapsibleNavbar } from "./components/ui/collapsible-navbar";
import { BentoGrid } from "./components/ui/bento-grid";

type View = "overview" | "orchestration" | "facts" | "usage" | "report";
const VIEWS: { id: View; label: string; icon: typeof LayoutGrid }[] = [
  { id: "overview", label: "Overview", icon: LayoutGrid },
  { id: "orchestration", label: "Orchestration", icon: Workflow },
  { id: "facts", label: "Hive memory", icon: Database },
  { id: "usage", label: "Budget", icon: Gauge },
  { id: "report", label: "Report", icon: FileText },
];

function SidebarNav({ view, onSelect }: { view: View; onSelect: (v: View) => void }) {
  const { open, setOpen } = useSidebar();
  return (
    <>
      <nav className="flex flex-col gap-1" aria-label="views">
        {VIEWS.map(v => {
          const Icon = v.icon;
          return (
            <SidebarLink
              key={v.id}
              link={{
                label: v.label,
                icon: <Icon className="size-4" strokeWidth={1.75} />,
                active: view === v.id,
                onClick: () => { onSelect(v.id); setOpen(false); },
              }}
            />
          );
        })}
      </nav>
      <div className="mt-auto px-3 pt-4">
        <p className={cn(
          "font-mono text-[10px] uppercase tracking-[0.14em] text-faint/70 transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}>
          full hive mind<br />coming soon
        </p>
      </div>
    </>
  );
}

export default function App() {
  const params = new URLSearchParams(location.search);
  const [demo, setDemo] = useState(params.has("demo") || params.get("mode") === "demo");
  const [runId, setRunId] = useState<string | null>(params.get("run"));
  const [view, setView] = useState<View>("orchestration");
  const live = useLiveRun(demo ? null : runId);
  const demoRun = useDemoRun(demo);
  const run: HiveRun | null = demo ? demoRun.run : live.run;
  const mainRef = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();

  const counts = useMemo(() => ({
    verified: run?.facts.filter(f => f.status === "verified").length ?? 0,
    rejected: run?.facts.filter(f => f.status === "rejected").length ?? 0,
    done: run?.tasks.filter(t => t.status === "done").length ?? 0,
    total: run?.tasks.length ?? 0,
    events: run?.events.length ?? 0,
    workers: run ? new Set(run.events.filter(e => e.kind === "claim").map(e => e.worker)).size : 0,
    budgetPct: run && run.budget_tokens > 0 ? Math.min(100, (run.spent_tokens / run.budget_tokens) * 100) : 0,
  }), [run]);

  const status = run ? runTone(run.status) : null;

  return (
    <Sidebar animate={!reduceMotion}>
      <div className="flex h-full">
        <SidebarBody>
          <SidebarNav view={view} onSelect={setView} />
        </SidebarBody>

        <div className="flex min-w-0 flex-1 flex-col">
          <CollapsibleNavbar containerRef={mainRef}>
            <div className="flex min-w-0 items-center gap-2.5">
              <SidebarToggle />
              <Hexagon className="size-[18px] flex-none text-accent" strokeWidth={2} />
              <EncryptedText
                text="HIVE LITE"
                revealDelayMs={85}
                flipDelayMs={45}
                className="font-mono text-[13px] font-bold tracking-[0.14em]"
                encryptedClassName="text-faint"
              />
              <span className="hidden text-[12px] text-faint md:inline">knull orchestration console</span>
            </div>
            <div className="flex flex-none items-center gap-2.5">
              {run && status && (
                <StatusBadge tone={status.tone} live={status.live}>{run.status.replace(/_/g, " ")}</StatusBadge>
              )}
              <div className="flex overflow-hidden rounded-md border border-line-strong" role="group" aria-label="data source">
                {(["live api", "demo replay"] as const).map(label => {
                  const isDemo = label === "demo replay";
                  const active = demo === isDemo;
                  return (
                    <button
                      key={label}
                      onClick={() => setDemo(isDemo)}
                      aria-pressed={active}
                      className={cn(
                        "px-2 py-1 font-mono text-[10.5px] uppercase tracking-[0.1em] transition-colors sm:px-2.5",
                        active ? "bg-overlay text-foreground" : "text-faint hover:text-muted",
                      )}
                    >
                      <span className="sm:hidden">{isDemo ? "demo" : "live"}</span>
                      <span className="hidden sm:inline">{label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </CollapsibleNavbar>

          <main ref={mainRef} className="dot-grid min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto flex min-h-full w-full max-w-[1120px] flex-col gap-5">
              {view === "overview" && (
                <>
                  <LaunchForm disabled={demo} onLaunch={async (o, w, b) => {
                    const id = await launchRun(o, w, b);
                    setDemo(false); setRunId(id); setView("orchestration");
                  }} />
                  {demo && (
                    <p className="text-[13px] text-muted">
                      Demo replay is on: a recorded offline hive run plays below. Switch to live API to launch a run against the server.
                    </p>
                  )}
                  {run && (
                    <BentoGrid>
                      <StatCard label="objective" value={run.objective} className="col-span-2 md:row-span-2" />
                      <StatCard label="status" value={run.status.replace(/_/g, " ")} tone={status?.tone} />
                      <StatCard label="tasks done" value={`${counts.done} / ${counts.total}`} />
                      <StatCard label="facts verified" value={counts.verified} tone="ok" />
                      <StatCard label="facts rejected" value={counts.rejected} tone={counts.rejected > 0 ? "bad" : undefined} />
                      <StatCard label="tokens spent" value={run.spent_tokens.toLocaleString()} />
                      <StatCard label="budget used" value={`${counts.budgetPct.toFixed(1)}%`} tone={counts.budgetPct > 85 ? "warn" : "info"} />
                      <StatCard label="symbiotes" value={counts.workers} />
                      <StatCard label="events" value={counts.events} />
                    </BentoGrid>
                  )}
                </>
              )}

              {view === "orchestration" && (
                run ? (
                  <div className="flex flex-1 flex-col gap-5">
                    <DagView tasks={run.tasks} events={run.events} />
                    <div className="grid flex-1 gap-5 lg:grid-cols-5 lg:grid-rows-1">
                      <WorkerPanel events={run.events} tasks={run.tasks} className="h-full lg:col-span-2" fill />
                      <EventLog events={run.events} className="h-full lg:col-span-3" fill />
                    </div>
                  </div>
                ) : (
                  <EmptyState>
                    {demo ? "Replay starting…" : "No run yet. Launch one from Overview, or switch on demo replay."}
                  </EmptyState>
                )
              )}

              {view === "facts" && (run
                ? <FactsPanel facts={run.facts} />
                : <EmptyState>{demo ? "Replay starting…" : "No run yet. Facts land here once a hive verifies them."}</EmptyState>)}

              {view === "usage" && (run
                ? <div className="flex flex-1 flex-col gap-5">
                    <BudgetGauge spent={run.spent_tokens} budget={run.budget_tokens} />
                    <UsagePanel usage={run.usage_by_route} className="flex-1" fill />
                  </div>
                : <EmptyState>{demo ? "Replay starting…" : "No run yet. Token usage lands here once a run starts."}</EmptyState>)}

              {view === "report" && (run?.report
                ? <ReportView report={run.report} />
                : <EmptyState>{demo ? "The report assembles when the replay finishes." : "No report yet. It assembles when a run completes."}</EmptyState>)}
            </div>
          </main>
        </div>
      </div>
    </Sidebar>
  );
}
