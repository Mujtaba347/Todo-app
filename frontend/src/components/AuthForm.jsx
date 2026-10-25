import { useState } from "react";
import { api, setToken } from "../api.js";

export default function AuthForm({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ identifier: "", email: "", username: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await api.post("/auth/register", {
          email: form.email,
          username: form.username,
          password: form.password,
        });
      }
      const identifier = mode === "register" ? form.email : form.identifier;
      const { access_token } = await api.post("/auth/login", { identifier, password: form.password });
      setToken(access_token);
      onLogin(await api.get("/auth/me"));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <div className="auth-hero">
        <div className="logo logo-lg">✓</div>
        <h1>Taskly</h1>
        <p>Plan your day, tick things off, and let your AI assistant do the typing.</p>
      </div>

      <form className="card auth-card" onSubmit={submit}>
        <div className="tabs">
          <button type="button" className={mode === "login" ? "tab active" : "tab"} onClick={() => setMode("login")}>
            Sign in
          </button>
          <button
            type="button"
            className={mode === "register" ? "tab active" : "tab"}
            onClick={() => setMode("register")}
          >
            Create account
          </button>
        </div>

        {mode === "login" ? (
          <label>
            Email or username
            <input value={form.identifier} onChange={set("identifier")} autoFocus required />
          </label>
        ) : (
          <>
            <label>
              Email
              <input type="email" value={form.email} onChange={set("email")} autoFocus required />
            </label>
            <label>
              Username
              <input value={form.username} onChange={set("username")} minLength={3} required />
            </label>
          </>
        )}
        <label>
          Password
          <input type="password" value={form.password} onChange={set("password")} minLength={mode === "register" ? 8 : undefined} required />
        </label>
        {mode === "register" && <div className="hint">At least 8 characters, with a letter and a number.</div>}

        {error && <div className="alert">{error}</div>}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>
    </div>
  );
}
