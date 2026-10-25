import { useCallback, useEffect, useState } from "react";
import { api, qs } from "../api.js";
import TodoForm from "../components/TodoForm.jsx";
import TodoItem from "../components/TodoItem.jsx";
import ChatWidget from "../components/ChatWidget.jsx";

const FILTERS = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "done", label: "Completed" },
];

export default function UserDashboard({ me }) {
  const [todos, setTodos] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const completed = filter === "all" ? undefined : filter === "done";
      const [list, s] = await Promise.all([
        api.get(`/todos${qs({ completed, search: search.trim() })}`),
        api.get("/todos/stats"),
      ]);
      setTodos(list);
      setStats(s);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [filter, search]);

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce search typing
    return () => clearTimeout(t);
  }, [load]);

  const create = async (payload) => {
    await api.post("/todos", payload);
    await load();
  };
  const update = async (id, payload) => {
    await api.put(`/todos/${id}`, payload);
    await load();
  };
  const toggle = (todo) => update(todo.id, { completed: !todo.completed }).catch((e) => setError(e.message));
  const remove = async (todo) => {
    if (!window.confirm(`Delete "${todo.title}"?`)) return;
    try {
      await api.del(`/todos/${todo.id}`);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <>
      <section className="page-head">
        <h2>Hello, {me.username}</h2>
        <p className="muted">Here's what's on your plate.</p>
      </section>

      {stats && (
        <section className="stats">
          <Stat label="Total" value={stats.total} />
          <Stat label="Pending" value={stats.pending} />
          <Stat label="Completed" value={stats.completed} />
          <Stat label="Overdue" value={stats.overdue} danger={stats.overdue > 0} />
        </section>
      )}

      <section className="card">
        <TodoForm onSubmit={create} />
      </section>

      <section className="card">
        <div className="toolbar">
          <div className="tabs">
            {FILTERS.map((f) => (
              <button key={f.key} className={filter === f.key ? "tab active" : "tab"} onClick={() => setFilter(f.key)}>
                {f.label}
              </button>
            ))}
          </div>
          <input
            className="search"
            placeholder="Search todos…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {error && <div className="alert">{error}</div>}
        {todos.length === 0 ? (
          <div className="empty">Nothing here yet. Add a todo above, or ask the assistant ✦</div>
        ) : (
          <ul className="todo-list">
            {todos.map((t) => (
              <TodoItem key={t.id} todo={t} onToggle={toggle} onUpdate={update} onDelete={remove} />
            ))}
          </ul>
        )}
      </section>

      <ChatWidget role="user" userId={me.id} onAction={load} />
    </>
  );
}

function Stat({ label, value, danger }) {
  return (
    <div className={`stat ${danger ? "stat-danger" : ""}`}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
