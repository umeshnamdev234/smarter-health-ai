// Per-browser persistence. Wrapped in try/catch: storage can be full or blocked.
import type { Chat } from "./types";

export function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

/** Saves chats; if storage is full (images are large), retries without image data. */
export function saveChats(chats: Chat[]) {
  if (save("sh.chats", chats)) return;
  save(
    "sh.chats",
    chats.map((c) => ({ ...c, messages: c.messages.map((m) => ({ ...m, images: undefined })) })),
  );
}
