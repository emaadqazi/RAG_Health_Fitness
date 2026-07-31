import type { Citation } from "@/lib/api";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 border-t border-zinc-200 pt-3 text-sm dark:border-zinc-800">
      <p className="mb-1 font-medium text-zinc-500 dark:text-zinc-400">Sources</p>
      <ol className="space-y-1">
        {citations.map((c) => (
          <li key={c.key} className="text-zinc-600 dark:text-zinc-400">
            <span className="text-zinc-400 dark:text-zinc-500">[{c.key}]</span>{" "}
            {c.link ? (
              <a href={c.link} target="_blank" rel="noopener noreferrer" className="underline hover:text-zinc-900 dark:hover:text-zinc-100">
                {c.title}
              </a>
            ) : (
              c.title
            )}{" "}
            {c.year ? `(${c.year})` : ""}
          </li>
        ))}
      </ol>
    </div>
  );
}
