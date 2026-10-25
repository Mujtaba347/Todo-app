import { useCallback, useEffect, useState } from "react";
import { api, qs } from "../api.js";
import TodoForm from "../components/TodoForm.jsx";
import TodoItem from "../components/TodoItem.jsx";
import ChatWidget from "../components/ChatWidget.jsx";

const TABS = ["Overview", "Users", "Todos", "Activity"];

export default function AdminDashboard({ me }) {
  const [tab, setTab] = useState("Overview");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [todos, setTodos] = useState([]);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");

  // Todo filters
  const [ownerFilter, setOwnerFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    try {
      const completed = statusFilter === "" ? undefined : statusFilter === "done";
      const [s, u, t, a] = await Promise.all([
        api.get("/admin/stats"),
        api.get("/admin/users"),
        api.get(`/admin/todos${qs({ owner_id: ownerFilter, completed, search: search.trim() })}`),
        api.get("/admin/audit?limit=100"),
      ]);
      setStats(s);
      setUsers(u);
      setTodos(t);
      setAudit(a);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  }, [ownerFilter, statusFilter, search]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const guard = (fn) => async (...args) => {
    try {
      await fn(...args);
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  // ---- users
  const createUser = async (payload) => {
    await api.post("/admin/users", payload);
    await load();
  };
  const updateUser = guard((id, payload) => api.put(`/admin/users/${id}`, payload));
  const deleteUser = guard(async (u) => {
    if (!window.confirm(`Delete ${u.username} and ALL of their todos?`)) return;
    await api.del(`/admin/users/${u.id}`);
  });

  // ---- todos
  const createTodo = async (payload) => {
    await api.post("/admin/todos", payload);
    await load();
  };
  const updateTodo = async (id, payload) => {
    await api.put(`/admin/todos/${id}`, payload);
    await load();
  };
  const toggleTodo = guard((t) => api.put(`/admin/todos/${t.id}`, { completed: !t.completed }));
  const deleteTodo = guard(async (t) => {
    if (!window.confirm(`Delete "${t.title}"?`)) return;
    await api.del(`/admin/todos/${t.id}`);
  });

  return (
    <>
      <section className="page-head">
        <h2>Admin console</h2>
        <p className="muted">Manage every user and every todo.</p>
      </section>

      <div className="tabs tabs-lg">
        {TABS.map((t) => (
          <button key={t} className={tab === t ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {error && <div className="alert">{error}</div>}

      {tab === "Overview" && stats && (
        <section className="stats stats-wide">
          <Stat label="Users" value={stats.users} />
          <Stat label="Active users" value={stats.active_users} />
          <Stat label="Admins" value={stats.admins} />
          <Stat label="Total todos" value={stats.total} />
          <Stat label="Pending" value={stats.pending} />
          <Stat label="Completed" value={stats.completed} />
          <Stat label="High priority pending" value={stats.high_priority_pending} />
          <Stat label="Overdue" value={stats.overdue} danger={stats.overdue > 0} />
        </section>
      )}

      {tab === "Users" && (
        <>
          <section className="card">
            <h3>Add user</h3>
            <UserForm onSubmit={createUser} />
          </section>
          <section className="card table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const self = u.id === me.id;
                  return (
                    <tr key={u.id}>
                      <td>{u.id}</td>
                      <td>
                        {u.username} {self && <span className="muted">(you)</span>}
                      </td>
                      <td>{u.email}</td>
                      <td>
                        <select
                          value={u.role}
                          disabled={self}
                          onChange={(e) => updateUser(u.id, { role: e.target.value })}
                        >
                          <option value="user">user</option>
                          <option value="admin">admin</option>
                        </select>
                      </td>
                      <td>
                        <button
                          className={`pill ${u.is_active ? "pill-low" : "pill-high"} pill-btn`}
                          disabled={self}
                          onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                        >
                          {u.is_active ? "active" : "disabled"}
                        </button>
                      </td>
                      <td className="right">
                        <button className="btn btn-danger btn-sm" disabled={self} onClick={() => deleteUser(u)}>
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </>
      )}

      {tab === "Todos" && (
        <>
          <section className="card">
            <h3>Add todo for a user</h3>
            <TodoForm owners={users} onSubmit={createTodo} />
          </section>
          <section className="card">
            <div className="toolbar">
              <select value={ownerFilter} onChange={(e) => setOwnerFilter(e.target.value)}>
                <option value="">All users</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username}
                  </option>
                ))}
              </select>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="">Any status</option>
                <option value="active">Active</option>
                <option value="done">Completed</option>
              </select>
              <input
                className="search"
                placeholder="Search todos…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            {todos.length === 0 ? (
              <div className="empty">No todos match.</div>
            ) : (
              <ul className="todo-list">
                {todos.map((t) => (
                  <TodoItem
                    key={t.id}
                    todo={t}
                    showOwner
                    onToggle={toggleTodo}
                    onUpdate={updateTodo}
                    onDelete={deleteTodo}
                  />
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {tab === "Activity" && (
        <section className="card table-wrap">
          <h3 style={{ marginTop: 12 }}>Assistant activity</h3>
          <p className="muted" style={{ margin: "0 0 8px" }}>
            Every chatbot message and every action it took (latest 100). Passwords are never stored here.
          </p>
          {audit.length === 0 ? (
            <div className="empty">No activity yet.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>Type</th>
                  <th>Details</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id}>
                    <td>{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</td>
                    <td>{a.username}</td>
                    <td>{a.kind === "chat" ? "message" : a.tool}</td>
                    <td className="audit-detail">{a.detail}</td>
                    <td>
                      <span className={`pill ${a.ok ? "pill-low" : "pill-high"}`}>{a.ok ? "ok" : "failed"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      <ChatWidget role="admin" userId={me.id} onAction={load} />
    </>
  );
}

function UserForm({ onSubmit }) {
  const blank = { email: "", username: "", password: "", role: "user" };
  const [form, setForm] = useState(blank);
  const [error, setError] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await onSubmit(form);
      setForm(blank);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <form className="form-row wrap" onSubmit={submit}>
      <input type="email" placeholder="Email" value={form.email} onChange={set("email")} required />
      <input placeholder="Username" value={form.username} onChange={set("username")} minLength={3} required />
      <input type="password" placeholder="Password" value={form.password} onChange={set("password")} minLength={8} required />
      <select value={form.role} onChange={set("role")}>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>
      <button className="btn btn-primary">Create user</button>
      {error && <div className="alert full">{error}</div>}
    </form>
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
