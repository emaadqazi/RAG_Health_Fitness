export type SubTopic = {
  label: string;
  search_query: string;
  rationale: string;
};

export type SourcePaper = {
  title: string;
  year: number | null;
  link: string;
  sources: string[];
};

export type Excerpt = {
  text: string;
  section: string;
};

export type Citation = {
  key: number;
  title: string;
  year: number | null;
  link: string;
  excerpts: Excerpt[];
};

export type SelectedChunk = {
  title: string;
  link: string;
  distance: number;
  section: string;
  cited: boolean;
};

export type RetrievalDetail = {
  label: string;
  search_query: string;
  candidates_by_source: Record<string, number>;
  selected: SelectedChunk[];
};

export type ChatEvent =
  | { type: "decomposition"; data: { subtopics: SubTopic[] } }
  | { type: "sources"; data: { papers: SourcePaper[] } }
  | { type: "token"; data: { text: string } }
  | { type: "done"; data: { citations: Citation[]; retrieval_detail: RetrievalDetail[] } }
  | { type: "error"; data: { message: string } };

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

/**
 * Streams SSE events from POST /api/chat. Uses fetch + ReadableStream (not
 * EventSource) because EventSource can't send a POST body.
 */
export async function* streamChat(question: string, signal?: AbortSignal): AsyncGenerator<ChatEvent> {
  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    if (response.status === 429) {
      yield { type: "error", data: { message: "Daily question limit reached. Please try again tomorrow." } };
      return;
    }
    yield { type: "error", data: { message: detail || `Request failed (${response.status})` } };
    return;
  }
  if (!response.body) {
    yield { type: "error", data: { message: "No response body from server." } };
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const raw of events) {
      const event = parseSseEvent(raw);
      if (event) yield event;
    }
  }
}

function parseSseEvent(raw: string): ChatEvent | null {
  let eventType = "";
  let dataLine = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event: ")) eventType = line.slice("event: ".length).trim();
    else if (line.startsWith("data: ")) dataLine += line.slice("data: ".length);
  }
  if (!eventType || !dataLine) return null;
  try {
    return { type: eventType, data: JSON.parse(dataLine) } as ChatEvent;
  } catch {
    return null;
  }
}
