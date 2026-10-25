import { useState } from "react";
import TodoForm from "./TodoForm.jsx";

const today = () => new Date().toISOString().slice(0, 10);

export default function TodoItem({ todo, showOwner, onToggle, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);
  const overdue = !todo.completed && todo.due_date && todo.due_date < today();

  if (editing) {
    return (
      <li className="todo editing">
        <TodoForm
          initial={todo}
          submitLabel="Save"
          onCancel={() => setEditing(false)}
          onSubmit={async (payload) => {
            delete payload.owner_id;
            await onUpdate(todo.id, payload);
            setEditing(false);
          }}
        />
      </li>
    );
  }

  return (
    <li className={`todo ${todo.completed ? "done" : ""}`}>
      <input
        type="checkbox"
        className="check"
        checked={todo.completed}
        onChange={() => onToggle(todo)}
        aria-label="Mark complete"
      />
      <div className="todo-body">
        <div className="todo-title">{todo.title}</div>
        {todo.description && <div className="todo-desc">{todo.description}</div>}
        <div className="todo-meta">
          <span className={`pill pill-${todo.priority}`}>{todo.priority}</span>
          {todo.due_date && (
            <span className={overdue ? "meta overdue" : "meta"}>
              {overdue ? "Overdue · " : "Due "}
              {todo.due_date}
            </span>
          )}
          {showOwner && <span className="meta">👤 {todo.owner_username}</span>}
        </div>
      </div>
      <div className="todo-actions">
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
          Edit
        </button>
        <button className="btn btn-danger btn-sm" onClick={() => onDelete(todo)}>
          Delete
        </button>
      </div>
    </li>
  );
}
