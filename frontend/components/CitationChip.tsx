"use client";

import { createContext, useContext, useState } from "react";
import type { Citation } from "@/lib/api";

// Populated by MessageBubble per-message so the stable `citation-chip` renderer
// (registered once in react-markdown's components map) can look up excerpt data
// without react-markdown re-creating component instances on every token.
export const CitationsContext = createContext<Map<number, Citation>>(new Map());

function CitationPopover({ citation, onClose }: { citation: Citation; onClose: () => void }) {
  const excerpt = citation.excerpts[0];
  return (
    <span
      role="dialog"
      className="absolute bottom-full left-1/2 z-20 mb-1.5 w-64 -translate-x-1/2 rounded-lg border border-zinc-200 bg-white p-3 text-left text-xs shadow-lg dark:border-zinc-700 dark:bg-zinc-900"
    >
      <span className="mb-1 block font-medium text-zinc-900 dark:text-zinc-100">{citation.title}</span>
      {excerpt && (
        <span className="mb-1.5 block leading-snug text-zinc-600 italic dark:text-zinc-400">
          &ldquo;{excerpt.text.length > 240 ? `${excerpt.text.slice(0, 240)}...` : excerpt.text}&rdquo;
        </span>
      )}
      <span className="flex items-center justify-between">
        {citation.link ? (
          <a href={citation.link} target="_blank" rel="noopener noreferrer" className="text-sky-700 underline dark:text-sky-400">
            View source
          </a>
        ) : (
          <span />
        )}
        <button type="button" onClick={onClose} className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200">
          Close
        </button>
      </span>
    </span>
  );
}

export function CitationChip({ n, citation }: { n: number; citation?: Citation }) {
  const [open, setOpen] = useState(false);

  if (!citation) {
    // Citation metadata hasn't arrived yet (mid-stream, before the `done` event) --
    // render as plain bracketed text rather than a non-functional chip.
    return <sup className="text-[0.7em]">[{n}]</sup>;
  }

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`Show source ${n}: ${citation.title}`}
        className="mx-0.5 inline-flex h-4 min-w-4 translate-y-[-1px] items-center justify-center rounded-full bg-sky-100 px-1 align-middle text-[10px] leading-none font-medium text-sky-800 hover:bg-sky-200 dark:bg-sky-900/50 dark:text-sky-300 dark:hover:bg-sky-900"
      >
        {n}
      </button>
      {open && <CitationPopover citation={citation} onClose={() => setOpen(false)} />}
    </span>
  );
}

/** Stable component reference registered in react-markdown's `components` map. */
export function CitationChipRenderer({ n }: { n: number }) {
  const citationsByKey = useContext(CitationsContext);
  return <CitationChip n={n} citation={citationsByKey.get(n)} />;
}
