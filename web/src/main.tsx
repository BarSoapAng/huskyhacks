import React, { FormEvent, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { supabase } from "./supabase";

type UserSession = {
  username: string;
  signedInAt: string;
};

const SESSION_KEY = "huskyhacks.session";

function App() {
  const [session, setSession] = useState<UserSession | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const savedSession = window.localStorage.getItem(SESSION_KEY);
    if (savedSession) {
      setSession(JSON.parse(savedSession));
    }

    // Touch the client so Supabase config is validated by the bundle now,
    // while real auth/database tables can be added in the next iteration.
    void supabase.auth.getSession();
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!username.trim() || !password.trim()) {
      setError("Enter a username and password.");
      return;
    }

    const nextSession = {
      username: username.trim(),
      signedInAt: new Date().toISOString()
    };

    window.localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
    setSession(nextSession);
    setPassword("");
  }

  function handleSignOut() {
    window.localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setUsername("");
    setPassword("");
  }

  if (session) {
    return (
      <main className="dashboard-shell">
        <section className="dashboard-panel" aria-label="Dashboard">
          <div>
            <p className="eyebrow">HuskyHacks</p>
            <h1>Welcome, {session.username}</h1>
          </div>
          <button className="primary-action" type="button" onClick={handleSignOut}>
            Sign out
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="signin-shell">
      <section className="signin-card" aria-label="Sign in">
        <div className="brand-mark" aria-hidden="true">
          H
        </div>
        <h1>Sign in</h1>
        <p className="account-copy">Use your HuskyHacks account</p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          {error ? <p className="form-error">{error}</p> : null}

          <div className="form-actions">
            <button className="text-action" type="button">
              Create account
            </button>
            <button className="primary-action" type="submit">
              Sign in
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
