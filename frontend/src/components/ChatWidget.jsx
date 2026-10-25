import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

const SUGGESTIONS = {
  user: [
    "Add a high priority todo to call the dentist tomorrow",
    "What's still pending?",
    "Mark everything about groceries as done",
  ],
  admin: [
    "Give me a platform overview",
    "List all users and how many todos each has",
    "Which todos are overdue?",
  ],
};

const TOOL_LABELS = {
  list_todos: "Looked up todos",
  create_todo: "Created a todo",
  update_todo: "Updated a todo",
  delete_todo: "Deleted a todo",
  delete_completed_todos: "Deleted completed todos",
  get_stats: "Checked stats",
  list_users: "Looked up users",
  create_user: "Created a user",
  update_user: "Updated a user",
  delete_user: "Deleted a user",
  describe_schema: "Inspected the schema",
  run_sql: "Ran a SQL query",
};

/**
 * Floating assistant in the bottom-right corner.
 * role="user"  -> /api/chat/user  (own todos only)
 * role="admin" -> /api/chat/admin (whole database)
 * Each role/account keeps its own separate conversation.
 */
export default function ChatWidget({ role, userId, onAction }) {
  const storageKey = `chat:${role}:${userId}`;
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) || [];
    } catch {
      return [];
    }
  });
  const endRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(messages.slice(-60)));
    } catch {
      /* storage unavailable */
    }
  }, [messages, storageKey]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, open]);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || loading) return;
    const history = messages.filter((m) => !m.error).map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post(`/chat/${role}`, { message: content, history: history.slice(-20) });
      setMessages((m) => [...m, { role: "assistant", content: res.reply, actions: res.actions }]);
      if (res.actions?.length) onAction?.();
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: err.message, error: true }]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const title = role === "admin" ? "Admin Assistant" : "My Assistant";
  const subtitle = role === "admin" ? "Full access to users, todos & database" : "Manages your own todos";

  return (
    <>
      {open && (
        <section className="chat-panel" aria-label={title}>
          <header className="chat-head">
            <div>
              <div className="chat-title">{title}</div>
              <div className="chat-sub">{subtitle}</div>
            </div>
            <div className="chat-head-actions">
              {messages.length > 0 && (
                <button className="icon-btn" title="Clear conversation" onClick={() => setMessages([])}>
                  ⟲
                </button>
              )}
              <button className="icon-btn" title="Close" onClick={() => setOpen(false)}>
                ✕
              </button>
            </div>
          </header>

          <div className="chat-body">
            {messages.length === 0 && (
              <div className="chat-empty">
                <p>
                  Hi! Ask me to {role === "admin" ? "manage users, todos or query the database" : "add, change, complete or delete your todos"}.
                </p>
                {SUGGESTIONS[role].map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`msg msg-${m.role} ${m.error ? "msg-error" : ""}`}>
                <div className="bubble">{m.content}</div>
                {m.actions?.length > 0 && (
                  <div className="actions">
                    {m.actions.map((a, j) => (
                      <span key={j} className={`action ${a.ok ? "ok" : "fail"}`}>
                        {a.ok ? "✓" : "✕"} {TOOL_LABELS[a.tool] || a.tool}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="msg msg-assistant">
                <div className="bubble typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="chat-input">
            <textarea
              rows={1}
              maxLength={4000}
              placeholder="Type a message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button className="btn btn-primary" onClick={() => send()} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>
        </section>
      )}

      <button className="chat-fab" onClick={() => setOpen((o) => !o)} aria-label="Toggle assistant">
        {open ? "✕" : "✦"}
      </button>
    </>
  );
}
