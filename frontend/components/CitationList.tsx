import type { Citation } from "@/lib/api";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-3 border-t border-stone-200 pt-3 text-sm dark:border-stone-700">
      <p className="mb-1 font-medium text-stone-500 dark:text-stone-400">Sources</p>
      <ol className="space-y-1">
        {citations.map((c) => (
          <li key={c.key} className="text-stone-600 dark:text-stone-400">
            <span className="text-stone-400 dark:text-stone-500">[{c.key}]</span>{" "}
            {c.link ? (
              <a href={c.link} target="_blank" rel="noopener noreferrer" className="text-teal-700 underline hover:no-underline dark:text-teal-400">
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
