export type ProgressStage = "decomposing" | "searching" | "synthesizing" | "writing" | "cold_start";

const LABELS: Record<ProgressStage, string> = {
  cold_start: "Waking up the server — this can take up to a minute on first use...",
  decomposing: "Breaking down your question...",
  searching: "Searching PubMed, Semantic Scholar, and Europe PMC...",
  synthesizing: "Reading the evidence...",
  // Tokens are streaming in but the answer isn't revealed until it's complete (see
  // ChatWindow.tsx) -- this label is the only feedback during that stretch, which can
  // run 30-60s+, so it needs to read as "still working," not stalled.
  writing: "Writing your answer...",
};

export function ProgressStatus({ stage }: { stage: ProgressStage }) {
  return (
    <div className="flex items-center gap-2 text-sm text-stone-500 dark:text-stone-400">
      <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-teal-500 dark:bg-teal-400" />
      {LABELS[stage]}
    </div>
  );
}
