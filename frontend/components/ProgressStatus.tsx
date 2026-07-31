export type ProgressStage = "decomposing" | "searching" | "synthesizing" | "cold_start";

const LABELS: Record<ProgressStage, string> = {
  cold_start: "Waking up the server — this can take up to a minute on first use...",
  decomposing: "Breaking down your question...",
  searching: "Searching PubMed, Semantic Scholar, and Europe PMC...",
  synthesizing: "Reading the evidence and writing an answer...",
};

export function ProgressStatus({ stage }: { stage: ProgressStage }) {
  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-zinc-400 dark:bg-zinc-500" />
      {LABELS[stage]}
    </div>
  );
}
