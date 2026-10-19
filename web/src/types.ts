export type TaskStatus = "pending" | "claimed" | "done" | "exhausted" | "failed";
export interface HiveTask { id: string; kind: string; title: string; status: TaskStatus | string; attempt: number; deps: string[]; result?: any }
export interface Fact { id: string; task_id?: string; claim: string; status: string; note?: string; quote?: string; evidence_id?: string }
export interface UsageRow { layer: string; agent: string; provider: string; model: string; in_tok: number; out_tok: number; calls: number }
export interface HiveEvent { ts: number; kind: string; [k: string]: any }
export interface HiveRun {
  run_id: string; objective: string; status: string; report: string;
  spent_tokens: number; budget_tokens: number;
  tasks: HiveTask[]; facts: Fact[]; usage_by_route: UsageRow[]; events: HiveEvent[];
}
