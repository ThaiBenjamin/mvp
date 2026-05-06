"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LayoutIcon, LogOutIcon } from "@/components/icons";
import { api, ApiError } from "@/lib/api";
import type { SessionInfo } from "@/lib/api";

type Session = SessionInfo;

type LoginProps = {
  onLogin: (username: string, password: string) => Promise<void>;
  error: string | null;
};

const LoginForm = ({ onLogin, error }: LoginProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    await onLogin(username.trim(), password.trim());
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-xl rounded-[32px] border border-[var(--stroke)] bg-white p-10 shadow-[var(--shadow)]">
        <h1 className="font-display text-3xl font-semibold text-[var(--navy-dark)]">
          Project Management MVP
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
          Sign in with the demo credentials to access your Kanban board.
        </p>
        <form className="mt-8 flex flex-col gap-4" onSubmit={handleSubmit}>
          <label className="space-y-2 text-sm text-[var(--navy-dark)]">
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 outline-none"
              placeholder="user"
              autoComplete="username"
              required
            />
          </label>
          <label className="space-y-2 text-sm text-[var(--navy-dark)]">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 outline-none"
              placeholder="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : null}
          <button
            type="submit"
            disabled={loading}
            className="rounded-full bg-[var(--primary-blue)] px-6 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </div>
    </main>
  );
};

export default function AuthApp() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSession()
      .then(setSession)
      .catch(() => setSession({ authenticated: false }))
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = async (username: string, password: string) => {
    setError(null);
    try {
      const result = await api.login(username, password);
      setSession({ authenticated: true, username: result.username ?? username });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid username or password.");
        return;
      }
      setError("Unable to sign in. Please try again.");
    }
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } finally {
      setSession({ authenticated: false });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 px-6 py-16">
        <div className="mx-auto max-w-xl rounded-[32px] border border-[var(--stroke)] bg-white p-10 shadow-[var(--shadow)]">
          <p className="text-sm text-[var(--gray-text)]">Checking session...</p>
        </div>
      </div>
    );
  }

  if (!session?.authenticated) {
    return <LoginForm onLogin={handleLogin} error={error} />;
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen w-full max-w-[1800px] flex-col gap-5 px-5 pb-10 pt-5 lg:px-7">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[var(--stroke)] bg-white/85 px-5 py-3.5 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--navy-dark)] text-white">
              <LayoutIcon className="h-4 w-4" />
            </span>
            <div>
              <h1 className="font-display text-xl font-semibold leading-tight text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-2 rounded-full border border-[var(--stroke)] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent-yellow)]" />
              Organized by status
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-[var(--surface)] px-3 py-1.5 text-xs">
              <span className="text-[var(--gray-text)]">Signed in as</span>
              <span className="font-semibold text-[var(--primary-blue)]">
                {session.username || "user"}
              </span>
            </span>
            <button
              type="button"
              onClick={handleLogout}
              aria-label="Log out"
              title="Log out"
              className="inline-flex h-8 items-center gap-1.5 rounded-full border border-[var(--stroke)] bg-white px-3 text-xs font-semibold text-[var(--navy-dark)] transition hover:bg-[var(--surface)]"
            >
              <LogOutIcon className="h-3.5 w-3.5" />
              <span>Log out</span>
            </button>
          </div>
        </header>

        <KanbanBoard />
      </main>
    </div>
  );
}
