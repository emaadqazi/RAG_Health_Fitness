"use client";

import { useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "@/lib/api";
import { CitationChipRenderer, CitationsContext } from "./CitationChip";
import { CitationList } from "./CitationList";
import { ProgressStatus, type ProgressStage } from "./ProgressStatus";
import { remarkCitations } from "@/lib/remarkCitations";

export type Message = {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  progressStage?: ProgressStage;
  error?: string;
};

// Sized for chat-bubble width, not full-page prose -- default `prose` styling reads
// too large/spacious here.
//
// react-markdown passes a `node` prop (the mdast AST node) into every custom
// component -- it must be destructured out, not spread onto the native DOM element,
// or React renders it as a literal `node="[object Object]"` attribute.
//
// Kept as a stable module-level object (not rebuilt per-render): `citation-chip`
// reads its data from CitationsContext rather than a closure, specifically so its
// component identity doesn't change across renders -- otherwise React would remount
// every open citation popover (losing its open state) each time new tokens stream in.
const markdownComponents: Components = {
  h1: ({ node: _node, ...props }) => <h2 className="mb-1.5 mt-3 text-base font-semibold first:mt-0" {...props} />,
  h2: ({ node: _node, ...props }) => <h2 className="mb-1.5 mt-3 text-base font-semibold first:mt-0" {...props} />,
  h3: ({ node: _node, ...props }) => <h3 className="mb-1 mt-2.5 text-sm font-semibold first:mt-0" {...props} />,
  p: ({ node: _node, ...props }) => <p className="mb-2 text-sm leading-relaxed last:mb-0" {...props} />,
  strong: ({ node: _node, ...props }) => <strong className="font-semibold" {...props} />,
  em: ({ node: _node, ...props }) => <em className="italic" {...props} />,
  ul: ({ node: _node, ...props }) => <ul className="mb-2 ml-4 list-disc space-y-0.5 text-sm last:mb-0" {...props} />,
  ol: ({ node: _node, ...props }) => <ol className="mb-2 ml-4 list-decimal space-y-0.5 text-sm last:mb-0" {...props} />,
  li: ({ node: _node, ...props }) => <li className="leading-relaxed" {...props} />,
  a: ({ node: _node, ...props }) => (
    <a className="underline underline-offset-2 hover:no-underline" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  hr: () => <hr className="my-3 border-zinc-200 dark:border-zinc-800" />,
  code: ({ node: _node, ...props }) => <code className="rounded bg-zinc-200/70 px-1 py-0.5 text-xs dark:bg-zinc-800" {...props} />,
  blockquote: ({ node: _node, ...props }) => (
    <blockquote className="mb-2 border-l-2 border-zinc-300 pl-3 text-sm italic text-zinc-600 dark:border-zinc-700 dark:text-zinc-400" {...props} />
  ),
  table: ({ node: _node, ...props }) => <table className="mb-2 w-full border-collapse text-xs" {...props} />,
  th: ({ node: _node, ...props }) => <th className="border-b border-zinc-300 px-2 py-1 text-left font-semibold dark:border-zinc-700" {...props} />,
  td: ({ node: _node, ...props }) => <td className="border-b border-zinc-200 px-2 py-1 align-top dark:border-zinc-800" {...props} />,
  // Custom node from lib/remarkCitations.ts -- not a standard HTML tag, so it's not
  // in react-markdown's Components type; the cast at the call site covers this one key.
  "citation-chip": ({ n }: { n: number }) => <CitationChipRenderer n={n} />,
} as Components;

const remarkPlugins = [remarkGfm, remarkCitations];

// The synthesis prompt (backend/app/pipeline/prompts.py) instructs the model to open
// every answer with a "## Summary" section before the per-sub-topic reasoning -- pull
// that out to render as a visually distinct callout instead of just another paragraph.
function splitSummarySection(text: string): { summary: string | null; rest: string } {
  const match = text.match(/^##\s+Summary\s*\n([\s\S]*?)(?=\n##\s|$)/);
  if (!match) return { summary: null, rest: text };
  const summary = match[1].trim();
  const rest = text.slice((match.index ?? 0) + match[0].length).trim();
  return { summary: summary || null, rest };
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const citationsByKey = useMemo(() => new Map((message.citations ?? []).map((c) => [c.key, c])), [message.citations]);
  const { summary, rest } = message.role === "assistant" ? splitSummarySection(message.text) : { summary: null, rest: message.text };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 sm:max-w-[70%] ${
          isUser
            ? "bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900"
            : "bg-zinc-100 text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100"
        }`}
      >
        {message.progressStage && <ProgressStatus stage={message.progressStage} />}
        {message.error && <p className="text-sm text-red-600 dark:text-red-400">{message.error}</p>}
        <CitationsContext.Provider value={citationsByKey}>
          {summary && (
            <div className="mb-3 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 dark:border-sky-900/40 dark:bg-sky-950/30">
              <p className="mb-1 text-[11px] font-semibold tracking-wide text-sky-700 uppercase dark:text-sky-400">Summary</p>
              {/* react-markdown re-parses on every render, which is fine at chat-turn
                  scale (one message, a few KB). */}
              <ReactMarkdown remarkPlugins={remarkPlugins} components={markdownComponents}>
                {summary}
              </ReactMarkdown>
            </div>
          )}
          {rest && (
            <ReactMarkdown remarkPlugins={remarkPlugins} components={markdownComponents}>
              {rest}
            </ReactMarkdown>
          )}
        </CitationsContext.Provider>
        {message.citations && <CitationList citations={message.citations} />}
      </div>
    </div>
  );
}
