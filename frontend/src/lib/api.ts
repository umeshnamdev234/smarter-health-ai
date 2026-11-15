// Client for the Smarter Health FastAPI backend (../backend).
import type { ChatMessage, DoctorFilters, DoctorMeta, Recommendation } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Health {
  status: "ok" | "degraded";
  model: string;
  model_server: string;
  model_server_reachable: boolean;
  model_available: boolean;
}

export type StreamEvent =
  | { type: "meta"; model: string; emergency: boolean; emergency_notice: string | null }
  | { type: "delta"; text: string }
  | {
      type: "done";
      usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
      elapsed_s: number;
      time_to_first_token_s: number | null;
      tokens_per_s: number | null;
    }
  | { type: "error"; message: string };

async function errorDetail(res: Response): Promise<string> {
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
  } catch {
    return `HTTP ${res.status}`;
  }
}

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

export async function getModels(): Promise<{ default: string; models: string[] }> {
  const res = await fetch(`${API_URL}/api/models`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** Converts UI messages into the backend's request format. */
export function toApiMessages(messages: ChatMessage[]) {
  return messages
    .filter((m) => !m.error && (m.content || m.images?.length))
    .map((m) => ({
      role: m.role,
      content: m.content || "",
      images: (m.images ?? []).map((im) => ({ mime_type: im.type, data: im.data })),
    }));
}

/** Streams a reply from POST /api/chat/stream (Server-Sent Events). */
export async function* streamChat(
  body: { messages: ReturnType<typeof toApiMessages>; model?: string },
  signal: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  if (!res.body) throw new Error("Empty response from server");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    // SSE events are separated by a blank line
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const data = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trim())
        .join("");
      if (data) yield JSON.parse(data) as StreamEvent;
    }
  }
}

export async function getDoctorMeta(): Promise<DoctorMeta> {
  const res = await fetch(`${API_URL}/api/doctors/meta`, { cache: "no-store" });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}

/** Suggests doctors from the directory for a conversation (MedGemma triage + ranking). */
export async function recommendDoctors(
  messages: ChatMessage[],
  filters: DoctorFilters,
  previous?: Recommendation, // pass to re-rank with a new filter without re-running triage
  limit = 6,
): Promise<Recommendation> {
  const reuse = previous
    ? { specialties: previous.specialties.map((s) => s.name), conditions: previous.conditions, urgency: previous.urgency }
    : {};
  const res = await fetch(`${API_URL}/api/recommend-doctors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: toApiMessages(messages), ...filters, ...reuse, limit }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json();
}
