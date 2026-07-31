import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "@/lib/api";
import { CitationList } from "./CitationList";
import { ProgressStatus, type ProgressStage } from "./ProgressStatus";

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
};

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
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
        {message.text && (
          // react-markdown re-parses on every render, which is fine at chat-turn scale
          // (one message, a few KB). Partial/unclosed markdown mid-stream (e.g. an
          // unclosed "**") just renders as literal characters, no crash or layout break.
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {message.text}
          </ReactMarkdown>
        )}
        {message.citations && <CitationList citations={message.citations} />}
      </div>
    </div>
  );
}
