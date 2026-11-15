"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getDoctorMeta, getHealth, getModels, recommendDoctors, streamChat, toApiMessages } from "@/lib/api";
import { load, save, saveChats } from "@/lib/storage";
import type { Chat, ChatMessage, DoctorFilters, DoctorMeta, ImageAttachment, ServerStatus, Theme } from "@/lib/types";
import Composer from "./Composer";
import EmptyState, { type Suggestion } from "./EmptyState";
import { Lock, Menu } from "./Icons";
import MessageItem from "./MessageItem";
import Sidebar from "./Sidebar";

const THEMES: Theme[] = ["auto", "light", "dark"];
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

// Rendered client-only (see ClientRoot), so reading localStorage in initialisers is safe.
export default function ChatApp() {
  const [chats, setChats] = useState<Chat[]>(() =>
    // drop any in-flight doctor lookups left over from a previous session
    load<Chat[]>("sh.chats", []).map((c) => ({ ...c, messages: c.messages.map((m) => (m.recLoading ? { ...m, recLoading: false } : m)) })),
  );
  const [currentId, setCurrentId] = useState<string | null>(() => {
    const id = load<string | null>("sh.current", null);
    return id && load<Chat[]>("sh.chats", []).some((c) => c.id === id) ? id : null;
  });
  const [input, setInput] = useState("");
  const [images, setImages] = useState<ImageAttachment[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => load<Theme>("sh.theme", "auto"));
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState<string>(() => load<string>("sh.model", ""));
  const [doctorMeta, setDoctorMeta] = useState<DoctorMeta | null>(null);
  const [status, setStatus] = useState<ServerStatus>({ state: "loading", text: "Connecting…", sub: "Smarter Health API · :8000" });

  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const forceScroll = useRef(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const current = chats.find((c) => c.id === currentId) ?? null;
  const chatsRef = useRef(chats);
  useEffect(() => { chatsRef.current = chats; }, [chats]);

  /* ---------- persistence (skipped mid-stream to avoid writing on every token) ---------- */
  useEffect(() => {
    if (streaming) return;
    saveChats(chats);
    save("sh.current", currentId);
  }, [chats, currentId, streaming]);

  /* ---------- theme ---------- */
  useEffect(() => {
    const el = document.documentElement;
    if (theme === "auto") el.removeAttribute("data-theme");
    else el.setAttribute("data-theme", theme);
    save("sh.theme", theme);
  }, [theme]);

  /* ---------- backend status ---------- */
  const refreshStatus = useCallback(async () => {
    try {
      const h = await getHealth();
      if (!h.model_server_reachable) {
        setStatus({ state: "err", text: "Model server offline", sub: "Run: brew services start ollama" });
        return;
      }
      const m = await getModels();
      getDoctorMeta().then(setDoctorMeta).catch(() => {});
      setModels(m.models);
      setModel((prev) => (m.models.includes(prev) ? prev : m.models.find((n) => n.startsWith(m.default)) ?? m.models[0] ?? ""));
      setStatus(
        h.model_available
          ? { state: "ok", text: "MedGemma online", sub: `API :8000 · ${m.models.length} model${m.models.length === 1 ? "" : "s"}` }
          : { state: "warn", text: `Model "${h.model}" not found`, sub: "Check LLM_MODEL in backend/.env" },
      );
    } catch {
      setStatus({ state: "err", text: "API offline", sub: "Run: backend/run.sh" });
    }
  }, []);

  useEffect(() => {
    // Initial check fires on the next tick; then poll while idle.
    const first = setTimeout(refreshStatus, 0);
    const id = setInterval(() => { if (!abortRef.current) refreshStatus(); }, 15000);
    return () => { clearTimeout(first); clearInterval(id); };
  }, [refreshStatus]);

  /* ---------- auto-scroll ---------- */
  useEffect(() => {
    const s = scrollRef.current;
    if (!s) return;
    if (forceScroll.current || s.scrollHeight - s.scrollTop - s.clientHeight < 160) {
      s.scrollTop = s.scrollHeight;
      forceScroll.current = false;
    }
  }, [chats, currentId]);

  /* ---------- streaming ---------- */
  const runStream = useCallback(
    async (chatId: string, history: ChatMessage[]) => {
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setStreaming(true);
      forceScroll.current = true;

      setChats((cs) => cs.map((c) => (c.id === chatId ? { ...c, messages: [...history, { role: "assistant", content: "" }], updated: Date.now() } : c)));
      const patch = (p: Partial<ChatMessage>) =>
        setChats((cs) =>
          cs.map((c) => {
            if (c.id !== chatId) return c;
            const msgs = c.messages.slice();
            msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...p };
            return { ...c, messages: msgs };
          }),
        );

      let content = "";
      let failed = false;
      let raf = 0;
      const flush = () => { raf = 0; patch({ content }); };

      try {
        for await (const ev of streamChat({ messages: toApiMessages(history), model: model || undefined }, ctrl.signal)) {
          if (ev.type === "meta" && ev.emergency) patch({ emergency: ev.emergency_notice });
          else if (ev.type === "delta") { content += ev.text; if (!raf) raf = requestAnimationFrame(flush); }
          else if (ev.type === "done") patch({ stats: ev.tokens_per_s ? `${ev.tokens_per_s} tok/s` : `${ev.elapsed_s}s` });
          else if (ev.type === "error") throw new Error(ev.message);
        }
      } catch (err) {
        const e = err as Error;
        if (e.name !== "AbortError") {
          failed = true;
          patch({ error: /fetch|network|load failed/i.test(e.message) ? "Cannot reach the Smarter Health API. Start it with: backend/run.sh" : `Error: ${e.message}` });
        }
      } finally {
        cancelAnimationFrame(raf);
        patch({ content: content || (failed ? "" : "_Stopped._") });
        setChats((cs) => cs.map((c) => (c.id === chatId ? { ...c, updated: Date.now() } : c)));
        abortRef.current = null;
        setStreaming(false);
        refreshStatus();
      }
    },
    [model, refreshStatus],
  );

  const send = useCallback(
    (text?: string) => {
      const t = (text ?? input).trim();
      if ((!t && !images.length) || streaming) return;
      const userMsg: ChatMessage = { role: "user", content: t, images: images.length ? images : undefined };
      let chat = current;
      if (!chat) {
        chat = { id: uid(), title: (t || "Image analysis").slice(0, 48), messages: [], updated: Date.now() };
        const created = chat;
        setChats((cs) => [...cs, created]);
        setCurrentId(created.id);
      }
      setInput("");
      setImages([]);
      runStream(chat.id, [...chat.messages, userMsg]);
    },
    [input, images, streaming, current, runStream],
  );

  const stop = () => abortRef.current?.abort();

  /* ---------- doctor suggestions ---------- */
  const findDoctors = useCallback(
    async (index: number, filters: DoctorFilters) => {
      const chat = chatsRef.current.find((c) => c.id === currentId);
      if (!chat) return;
      const chatId = chat.id;
      const history = chat.messages.slice(0, index + 1);
      const previous = chat.messages[index]?.recommendation; // reuse triage when only filters change
      const patchMsg = (p: Partial<ChatMessage>) =>
        setChats((cs) =>
          cs.map((c) => (c.id !== chatId ? c : { ...c, messages: c.messages.map((m, i) => (i === index ? { ...m, ...p } : m)) })),
        );
      patchMsg({ recLoading: true, recError: undefined });
      try {
        const rec = await recommendDoctors(history, filters, previous);
        // keep the model's explanations when re-ranking
        patchMsg({ recommendation: previous ? { ...rec, specialties: previous.specialties, source: previous.source } : rec, recLoading: false });
      } catch (err) {
        const msg = (err as Error).message;
        patchMsg({ recLoading: false, recError: /fetch|network|load failed/i.test(msg) ? "Cannot reach the Smarter Health API." : msg });
      }
    },
    [currentId],
  );

  const regenerate = useCallback(() => {
    if (!current || streaming) return;
    const msgs = current.messages.slice();
    if (msgs.at(-1)?.role === "assistant") msgs.pop();
    runStream(current.id, msgs);
  }, [current, streaming, runStream]);

  /* ---------- sidebar actions ---------- */
  const selectChat = (id: string) => { stop(); forceScroll.current = true; setCurrentId(id); setSidebarOpen(false); };
  const newChat = () => { stop(); setCurrentId(null); setSidebarOpen(false); textareaRef.current?.focus(); };
  const deleteChat = (id: string) => {
    if (id === currentId) { stop(); setCurrentId(null); }
    setChats((cs) => cs.filter((c) => c.id !== id));
  };
  const clearAll = () => {
    if (!confirm("Delete all conversations?")) return;
    stop(); setChats([]); setCurrentId(null);
  };

  const pickSuggestion = (s: Suggestion) => {
    if (s.image) {
      setInput("Please analyze this medical image and describe any notable findings.");
      fileInputRef.current?.click();
    } else send(s.prompt);
  };

  const lastIndex = (current?.messages.length ?? 0) - 1;

  return (
    <div className={`app ${sidebarOpen ? "open" : ""}`}>
      <Sidebar
        chats={chats}
        currentId={currentId}
        status={status}
        theme={theme}
        onSelect={selectChat}
        onDelete={deleteChat}
        onNew={newChat}
        onClearAll={clearAll}
        onCycleTheme={() => setTheme((t) => THEMES[(THEMES.indexOf(t) + 1) % THEMES.length])}
      />
      <div className="scrim" onClick={() => setSidebarOpen(false)} />

      <main className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" aria-label="Open menu" onClick={() => setSidebarOpen(true)}><Menu /></button>
          <div className="model-pill">
            <select
              aria-label="Model"
              value={model}
              onChange={(e) => { setModel(e.target.value); save("sh.model", e.target.value); }}
            >
              {models.length === 0 && <option value="">medgemma</option>}
              {models.map((m) => <option key={m} value={m}>{m.replace(":latest", "")}</option>)}
            </select>
            <span className="badge">MED</span>
          </div>
          <div className="spacer" />
          <div className="privacy" title="All processing happens on this device">
            <Lock stroke="var(--accent)" /><span>Private · runs on your device</span>
          </div>
        </header>

        <div className="scroll" ref={scrollRef}>
          {!current || current.messages.length === 0 ? (
            <EmptyState onPick={pickSuggestion} />
          ) : (
            <div className="thread">
              {current.messages.map((m, i) => (
                <MessageItem
                  key={i}
                  message={m}
                  index={i}
                  meta={doctorMeta}
                  onFindDoctors={findDoctors}
                  isLast={i === lastIndex}
                  streaming={streaming && i === lastIndex && m.role === "assistant"}
                  canRegenerate={!streaming}
                  onRegenerate={regenerate}
                />
              ))}
            </div>
          )}
        </div>

        <Composer
          value={input}
          onChange={setInput}
          images={images}
          onImagesChange={setImages}
          streaming={streaming}
          onSend={() => send()}
          onStop={stop}
          fileInputRef={fileInputRef}
          textareaRef={textareaRef}
        />
      </main>
    </div>
  );
}
