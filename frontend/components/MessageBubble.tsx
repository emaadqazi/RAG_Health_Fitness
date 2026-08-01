"use client";

import { useCallback, useMemo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation, RetrievalDetail } from "@/lib/api";
import { CitationChipRenderer, CitationsContext } from "./CitationChip";
import { CitationList } from "./CitationList";
import { ProgressStatus, type ProgressStage } from "./ProgressStatus";
import { SourceTransparencyPanel, type HighlightRequest } from "./SourceTransparencyPanel";
import { remarkCitations } from "@/lib/remarkCitations";

export type Message = {
  role: "user" | "assistant";
  text: string;
  citations?: Citation[];
  retrievalDetail?: RetrievalDetail[];
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
    <a className="text-teal-700 underline underline-offset-2 hover:no-underline dark:text-teal-400" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  hr: () => <hr className="my-3 border-stone-200 dark:border-stone-700" />,
  code: ({ node: _node, ...props }) => <code className="rounded bg-stone-200/70 px-1 py-0.5 text-xs dark:bg-stone-700" {...props} />,
  blockquote: ({ node: _node, ...props }) => (
    <blockquote className="mb-2 border-l-2 border-teal-300 pl-3 text-sm text-stone-600 italic dark:border-teal-700 dark:text-stone-400" {...props} />
  ),
  table: ({ node: _node, ...props }) => <table className="mb-2 w-full border-collapse text-xs" {...props} />,
  th: ({ node: _node, ...props }) => <th className="border-b border-stone-300 px-2 py-1 text-left font-semibold dark:border-stone-600" {...props} />,
  td: ({ node: _node, ...props }) => <td className="border-b border-stone-200 px-2 py-1 align-top dark:border-stone-700" {...props} />,
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

type ContentTab = { key: string; label: string; body: string };

// The synthesis prompt already emits one "## <sub-topic label>" header per sub-topic
// (matching the decomposition event's labels) after the Summary block -- split on
// every such boundary so each becomes its own tab instead of one long scroll. Only
// runs once on the complete text (see doc 06: buffering the full answer until `done`
// means there's no partially-streamed final section to worry about splitting).
function splitIntoSections(rest: string): ContentTab[] {
  if (!rest) return [];
  const chunks = rest.split(/\n(?=##\s+)/);
  const sections: ContentTab[] = [];
  chunks.forEach((chunk, i) => {
    const match = chunk.match(/^##\s+(.+?)\s*\n([\s\S]*)$/);
    if (match) {
      const body = match[2].trim();
      if (body) sections.push({ key: `section-${i}`, label: match[1].trim(), body });
    } else if (chunk.trim()) {
      // Text before any "## " header (or the model didn't follow the header
      // structure) -- keep it as an unlabeled leading tab rather than dropping it.
      sections.push({ key: `section-${i}`, label: "Answer", body: chunk.trim() });
    }
  });
  return sections;
}

const TAB_BUTTON_BASE = "-mb-px shrink-0 max-w-[10rem] truncate border-b-2 px-2 pb-1.5 text-xs font-medium";
const TAB_BUTTON_ACTIVE = "border-teal-600 text-teal-700 dark:border-teal-400 dark:text-teal-300";
const TAB_BUTTON_INACTIVE = "border-transparent text-stone-400 hover:text-stone-600 dark:hover:text-stone-300";
const SOURCES_TAB_KEY = "__sources__";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  // null until the user explicitly picks a tab -- lets the default (first sub-topic)
  // be computed fresh each render instead of getting locked in before content arrives.
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<HighlightRequest | null>(null);
  const citationsByKey = useMemo(() => new Map((message.citations ?? []).map((c) => [c.key, c])), [message.citations]);
  // Clicking a citation chip's "Show in Sources" backtracks to the matching entry:
  // switch to the Sources tab and trigger its scroll-into-view + highlight (doc 09).
  const onShowInSources = useCallback((key: number) => {
    setActiveTab(SOURCES_TAB_KEY);
    setHighlight({ key, nonce: Date.now() });
  }, []);
  const citationsContextValue = useMemo(() => ({ citationsByKey, onShowInSources }), [citationsByKey, onShowInSources]);
  const { summary, rest } = message.role === "assistant" ? splitSummarySection(message.text) : { summary: null, rest: message.text };
  const contentTabs = useMemo(() => splitIntoSections(rest), [rest]);
  // Retrieval detail (per-sub-topic candidate breakdown + relevance ranking) only
  // arrives with the `done` event, once synthesis has finished and citations are known.
  const hasSourceDetail = !isUser && (message.retrievalDetail?.length ?? 0) > 0;
  const tabKeys = [...contentTabs.map((t) => t.key), ...(hasSourceDetail ? [SOURCES_TAB_KEY] : [])];
  const showTabs = tabKeys.length > 1;
  const defaultTab = contentTabs[0]?.key ?? (hasSourceDetail ? SOURCES_TAB_KEY : null);
  const effectiveTab = activeTab && tabKeys.includes(activeTab) ? activeTab : defaultTab;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 sm:max-w-[70%] ${
          isUser
            ? "bg-teal-600 text-white"
            : "border border-stone-200 bg-white text-stone-900 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-100"
        }`}
      >
        {message.progressStage && <ProgressStatus stage={message.progressStage} />}
        {message.error && <p className="text-sm text-red-600 dark:text-red-400">{message.error}</p>}
        <CitationsContext.Provider value={citationsContextValue}>
          {summary && (
            <div className="mb-3 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 dark:border-teal-900/40 dark:bg-teal-950/30">
              <p className="mb-1 text-[11px] font-semibold tracking-wide text-teal-700 uppercase dark:text-teal-400">Summary</p>
              {/* react-markdown re-parses on every render, which is fine at chat-turn
                  scale (one message, a few KB). */}
              <ReactMarkdown remarkPlugins={remarkPlugins} components={markdownComponents}>
                {summary}
              </ReactMarkdown>
            </div>
          )}
          {showTabs && (
            <div className="mb-2 flex gap-3 overflow-x-auto border-b border-stone-200 dark:border-stone-700">
              {contentTabs.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  title={t.label}
                  onClick={() => setActiveTab(t.key)}
                  className={`${TAB_BUTTON_BASE} ${effectiveTab === t.key ? TAB_BUTTON_ACTIVE : TAB_BUTTON_INACTIVE}`}
                >
                  {t.label}
                </button>
              ))}
              {hasSourceDetail && (
                <button
                  type="button"
                  onClick={() => setActiveTab(SOURCES_TAB_KEY)}
                  className={`${TAB_BUTTON_BASE} ${effectiveTab === SOURCES_TAB_KEY ? TAB_BUTTON_ACTIVE : TAB_BUTTON_INACTIVE}`}
                >
                  Sources
                </button>
              )}
            </div>
          )}
          {contentTabs.map(
            (t) =>
              (!showTabs || effectiveTab === t.key) && (
                <ReactMarkdown key={t.key} remarkPlugins={remarkPlugins} components={markdownComponents}>
                  {t.body}
                </ReactMarkdown>
              )
          )}
        </CitationsContext.Provider>
        {message.citations && effectiveTab !== SOURCES_TAB_KEY && <CitationList citations={message.citations} />}
        {hasSourceDetail && effectiveTab === SOURCES_TAB_KEY && (
          <SourceTransparencyPanel detail={message.retrievalDetail!} highlight={highlight} />
        )}
      </div>
    </div>
  );
}
