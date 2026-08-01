"use client";

import { useRef, useState } from "react";
import { streamChat } from "@/lib/api";
import { MessageBubble, type Message } from "./MessageBubble";

const EXAMPLE_QUESTIONS = [
  "If I can run a half marathon in 1:30 but I smoke a pack of cigarettes a day, how is this going to impact my health?",
  "Does creatine supplementation affect kidney function in healthy adults?",
  "How much does chronic sleep deprivation blunt the benefits of strength training?",
];

const COLD_START_HINT_DELAY_MS = 4000;

export function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function ask(question: string) {
    if (!question.trim() || isStreaming) return;

    setInput("");
    setIsStreaming(true);
    setMessages((prev) => [...prev, { role: "user", text: question }, { role: "assistant", text: "", progressStage: "decomposing" }]);

    const controller = new AbortController();
    abortRef.current = controller;
    const coldStartTimer = setTimeout(() => {
      setMessages((prev) => updateLastAssistant(prev, (m) => ({ ...m, progressStage: "cold_start" })));
    }, COLD_START_HINT_DELAY_MS);

    // Tokens accumulate here silently rather than being written into message.text as
    // they arrive -- the whole answer (Summary callout, tabs, citation chips) commits
    // in one render once `done` lands, instead of the bubble growing/repainting and
    // forcing a scroll-chase the whole time synthesis is running.
    let streamingBuffer = "";
    let hasStartedWriting = false;

    try {
      for await (const event of streamChat(question, controller.signal)) {
        clearTimeout(coldStartTimer);
        if (event.type === "decomposition") {
          setMessages((prev) => updateLastAssistant(prev, (m) => ({ ...m, progressStage: "searching" })));
        } else if (event.type === "sources") {
          setMessages((prev) => updateLastAssistant(prev, (m) => ({ ...m, progressStage: "synthesizing" })));
        } else if (event.type === "token") {
          streamingBuffer += event.data.text;
          if (!hasStartedWriting) {
            hasStartedWriting = true;
            setMessages((prev) => updateLastAssistant(prev, (m) => ({ ...m, progressStage: "writing" })));
          }
        } else if (event.type === "done") {
          setMessages((prev) =>
            updateLastAssistant(prev, (m) => ({
              ...m,
              progressStage: undefined,
              text: streamingBuffer,
              citations: event.data.citations,
              retrievalDetail: event.data.retrieval_detail,
            }))
          );
        } else if (event.type === "error") {
          setMessages((prev) => updateLastAssistant(prev, (m) => ({ ...m, progressStage: undefined, error: event.data.message })));
        }
      }
    } catch {
      clearTimeout(coldStartTimer);
      setMessages((prev) =>
        updateLastAssistant(prev, (m) => ({ ...m, progressStage: undefined, error: "Connection lost. Please try again." }))
      );
    } finally {
      clearTimeout(coldStartTimer);
      setIsStreaming(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-8 sm:px-6">
      {messages.length === 0 && (
        <div className="flex flex-1 flex-col items-center justify-center gap-5 text-center">
          <p className="text-stone-500 dark:text-stone-400">Ask a health/fitness question grounded in published research.</p>
          <div className="flex flex-col gap-2">
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => ask(q)}
                className="rounded-full border border-stone-300 px-4 py-2 text-sm text-stone-700 transition-colors hover:border-teal-300 hover:bg-teal-50 dark:border-stone-700 dark:text-stone-300 dark:hover:border-teal-800 dark:hover:bg-teal-950/30"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto">
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="mt-5 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={isStreaming}
          maxLength={500}
          className="flex-1 rounded-full border border-stone-300 bg-white px-4 py-2.5 text-sm text-stone-900 outline-none transition-colors focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100 dark:focus:border-teal-400"
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="rounded-full bg-teal-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-teal-700 disabled:opacity-40 dark:bg-teal-600 dark:hover:bg-teal-500"
        >
          Ask
        </button>
      </form>
    </div>
  );
}

function updateLastAssistant(messages: Message[], update: (m: Message) => Message): Message[] {
  const next = [...messages];
  for (let i = next.length - 1; i >= 0; i--) {
    if (next[i].role === "assistant") {
      next[i] = update(next[i]);
      break;
    }
  }
  return next;
}
