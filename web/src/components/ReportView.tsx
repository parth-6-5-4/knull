import { marked } from "marked";
import { Panel } from "./ui";

export function ReportView({ report }: { report: string }) {
  const html = marked.parse(report, { async: false }) as string;
  return (
    <Panel title="Final report" meta={<span className="font-mono text-[10.5px] uppercase tracking-[0.12em] text-faint">verified facts only</span>}>
      <article className="report" dangerouslySetInnerHTML={{ __html: html }} />
    </Panel>
  );
}
