import { useState } from "react";

/**
 * Create / edit form shared by the user and admin dashboards.
 * `owners` (optional) renders an owner picker, used by the admin to create todos for a user.
 */
export default function TodoForm({ initial, owners, onSubmit, onCancel, submitLabel = "Add todo" }) {
  const [form, setForm] = useState({
    title: initial?.title || "",
    description: initial?.description || "",
    priority: initial?.priority || "medium",
    due_date: initial?.due_date || "",
    owner_id: initial?.owner_id || owners?.[0]?.id || "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = {
        title: form.title,
        description: form.description,
        priority: form.priority,
        due_date: form.due_date || null,
      };
      if (owners) payload.owner_id = Number(form.owner_id);
      await onSubmit(payload);
      if (!initial) setForm({ ...form, title: "", description: "", due_date: "" });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="todo-form" onSubmit={submit}>
      <input
        className="input-title"
        placeholder="What needs to be done?"
        value={form.title}
        onChange={set("title")}
        maxLength={200}
        required
      />
      <textarea placeholder="Details (optional)" rows={2} value={form.description} onChange={set("description")} />
      <div className="form-row">
        {owners && (
          <select value={form.owner_id} onChange={set("owner_id")} required title="Owner">
            {owners.map((o) => (
              <option key={o.id} value={o.id}>
                {o.username}
              </option>
            ))}
          </select>
        )}
        <select value={form.priority} onChange={set("priority")} title="Priority">
          <option value="low">Low priority</option>
          <option value="medium">Medium priority</option>
          <option value="high">High priority</option>
        </select>
        <input type="date" value={form.due_date} onChange={set("due_date")} title="Due date" />
        <div className="spacer" />
        {onCancel && (
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="btn btn-primary" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </button>
      </div>
      {error && <div className="alert">{error}</div>}
    </form>
  );
}
