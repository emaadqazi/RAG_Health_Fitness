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
        {message.text && <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.text}</p>}
        {message.citations && <CitationList citations={message.citations} />}
      </div>
    </div>
  );
}
