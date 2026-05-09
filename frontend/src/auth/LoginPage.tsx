import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { authApi } from "../api/auth";
import { ApiError } from "../api/client";
import { Button, Input } from "../design/primitives";
import { useAuth } from "../state/auth";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const setMe = useAuth((s) => s.setMe);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await authApi.login({ email, password });
      const me = await authApi.me();
      setMe(me);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center px-lg py-3xl">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-auth flex flex-col gap-xl"
        aria-labelledby="login-title"
      >
        <header className="flex flex-col gap-xs">
          <h1 id="login-title" className="t-title">Sign in</h1>
          <p className="t-small text-text-secondary">
            Welcome back to Velvic Monitor.
          </p>
        </header>
        <div className="flex flex-col gap-md">
          <label className="flex flex-col gap-xs">
            <span className="t-meta">Email</span>
            <Input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-xs">
            <span className="t-meta">Password</span>
            <Input
              type="password"
              autoComplete="current-password"
              required
              minLength={1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
        </div>
        {error !== null && (
          <p className="t-small text-signal-negative">{error}</p>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
        <p className="t-small text-text-secondary">
          New here?{" "}
          <a href="/signup" className="underline text-text-primary">
            Create an organisation
          </a>
        </p>
      </form>
    </div>
  );
}
