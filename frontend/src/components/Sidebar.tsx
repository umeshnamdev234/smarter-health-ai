"use client";

import { useMemo, useState } from "react";
import type { Chat, ServerStatus, Theme } from "@/lib/types";
import { ChatBubble, Moon, Plus, Pulse, Search, Trash } from "./Icons";

interface Props {
  chats: Chat[];
  currentId: string | null;
  status: ServerStatus;
  theme: Theme;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  onClearAll: () => void;
  onCycleTheme: () => void;
}

const DAY = 864e5;

export default function Sidebar({ chats, currentId, status, theme, onSelect, onDelete, onNew, onClearAll, onCycleTheme }: Props) {
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = chats.filter((c) => !q || c.title.toLowerCase().includes(q)).sort((a, b) => b.updated - a.updated);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const defs: [string, (t: number) => boolean][] = [
      ["Today", (t) => t >= today],
      ["Yesterday", (t) => t >= today - DAY],
      ["Previous 7 days", (t) => t >= today - 7 * DAY],
      ["Older", () => true],
    ];
    const used = new Set<string>();
    return defs
      .map(([label, fn]) => {
        const items = list.filter((c) => !used.has(c.id) && fn(c.updated));
        items.forEach((c) => used.add(c.id));
        return { label, items };
      })
      .filter((g) => g.items.length);
  }, [chats, query]);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="logo"><Pulse size={22} strokeWidth={2.6} /></div>
        <div>
          <div className="brand-name">Smarter <span>Health</span></div>
          <div className="brand-sub">AI Health Companion</div>
        </div>
      </div>

      <button className="new-chat" onClick={onNew}><Plus />New consultation</button>

      <div className="search">
        <Search opacity={0.6} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search chats" aria-label="Search chats" />
      </div>

      <nav className="history">
        {groups.length === 0 && <div className="group-label plain">No conversations yet</div>}
        {groups.map((g) => (
          <div key={g.label}>
            <div className="group-label">{g.label}</div>
            {g.items.map((c) => (
              <div
                key={c.id}
                role="button"
                tabIndex={0}
                className={`chat-item ${c.id === currentId ? "active" : ""}`}
                onClick={() => onSelect(c.id)}
                onKeyDown={(e) => e.key === "Enter" && onSelect(c.id)}
              >
                <ChatBubble opacity={0.7} />
                <span className="t">{c.title}</span>
                <button
                  className="del"
                  title="Delete"
                  aria-label={`Delete ${c.title}`}
                  onClick={(e) => { e.stopPropagation(); onDelete(c.id); }}
                >
                  <Trash />
                </button>
              </div>
            ))}
          </div>
        ))}
      </nav>

      <div className="side-foot">
        <div className="status">
          <span className={`dot ${status.state === "ok" ? "ok" : status.state === "err" ? "err" : ""}`} />
          <div>
            <span>{status.text}</span>
            <small>{status.sub}</small>
          </div>
        </div>
        <button className="side-btn" onClick={onCycleTheme}>
          <Moon />Theme: {theme[0].toUpperCase() + theme.slice(1)}
        </button>
        <button className="side-btn" onClick={onClearAll}><Trash size={16} />Clear all chats</button>
      </div>
    </aside>
  );
}
