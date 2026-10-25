import { useEffect, useState } from "react";
import { api, getToken, setToken } from "./api.js";
import AuthForm from "./components/AuthForm.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(!!getToken());

  useEffect(() => {
    if (!getToken()) return;
    api
      .get("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    const onLogout = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  if (booting) return <div className="boot">Loading…</div>;
  if (!user) return <AuthForm onLogin={setUser} />;

  const isAdmin = user.role === "admin";
  return (
    <div className="app" data-theme={isAdmin ? "admin" : "user"}>
      <header className="topbar">
        <div className="brand">
          <span className="logo">✓</span>
          <span className="brand-name">Taskly</span>
          {isAdmin && <span className="badge badge-admin">Admin</span>}
        </div>
        <div className="topbar-right">
          <span className="who">{user.username}</span>
          <button className="btn btn-ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>
      <main className="container">
        {isAdmin ? <AdminDashboard me={user} /> : <UserDashboard me={user} />}
      </main>
    </div>
  );
}
