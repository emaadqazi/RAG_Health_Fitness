import type { RetrievalDetail } from "@/lib/api";

const SOURCE_LABELS: Record<string, string> = {
  pubmed: "PubMed",
  semantic_scholar: "Semantic Scholar",
  europepmc: "Europe PMC",
};

export function SourceTransparencyPanel({ detail }: { detail: RetrievalDetail[] }) {
  if (detail.length === 0) {
    return <p className="py-2 text-sm text-stone-500 dark:text-stone-400">No retrieval detail available for this answer.</p>;
  }

  return (
    <div className="space-y-4 py-1">
      {detail.map((subtopic) => (
        <div key={subtopic.label}>
          <p className="text-sm font-semibold text-stone-800 dark:text-stone-200">{subtopic.label}</p>
          <p className="mb-1.5 text-xs text-stone-500 dark:text-stone-400">
            Searched: <span className="italic">&ldquo;{subtopic.search_query}&rdquo;</span>
          </p>
          <div className="mb-2 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-stone-500 dark:text-stone-400">
            {Object.entries(subtopic.candidates_by_source).map(([source, count]) => (
              <span key={source}>
                {SOURCE_LABELS[source] ?? source}: <span className="font-medium text-stone-700 dark:text-stone-300">{count}</span>
              </span>
            ))}
          </div>
          {subtopic.selected.length === 0 ? (
            <p className="text-xs text-stone-400 dark:text-stone-500">No chunks were relevant enough to select.</p>
          ) : (
            <ul className="space-y-1">
              {subtopic.selected.map((chunk, i) => (
                <li
                  key={i}
                  className={`flex items-start gap-2 rounded-md px-2 py-1 text-xs ${
                    chunk.cited
                      ? "bg-emerald-50 dark:bg-emerald-950/30"
                      : "opacity-60"
                  }`}
                >
                  <span
                    className={`mt-0.5 shrink-0 rounded px-1 py-0.5 font-mono text-[10px] ${
                      chunk.cited
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300"
                        : "bg-stone-200 text-stone-600 dark:bg-stone-700 dark:text-stone-400"
                    }`}
                    title="Cosine distance to the sub-topic query -- lower is more relevant"
                  >
                    {chunk.distance.toFixed(3)}
                  </span>
                  <span className="flex-1">
                    {chunk.link ? (
                      <a href={chunk.link} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline hover:no-underline dark:text-teal-400">
                        {chunk.title}
                      </a>
                    ) : (
                      chunk.title
                    )}{" "}
                    <span className="text-stone-400 dark:text-stone-500">({chunk.section})</span>
                    {chunk.cited && (
                      <span className="ml-1 font-medium text-emerald-700 dark:text-emerald-400">— cited in answer</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
