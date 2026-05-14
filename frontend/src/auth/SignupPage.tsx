import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { authApi } from "../api/auth";
import { ApiError } from "../api/client";
import { Button, Input } from "../design/primitives";
import { useAuth } from "../state/auth";

export function SignupPage() {
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
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
      await authApi.signup({
        org_name: orgName,
        email,
        password,
        ...(displayName ? { display_name: displayName } : {}),
      });
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
        aria-labelledby="signup-title"
      >
        <header className="flex flex-col gap-xs">
          <h1 id="signup-title" className="t-title">Create your organisation</h1>
          <p className="t-small text-text-secondary">
            Stand up a workspace for your IR team.
          </p>
        </header>
        <div className="flex flex-col gap-md">
          <label className="flex flex-col gap-xs">
            <span className="t-meta">Organisation name</span>
            <Input
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
            />
          </label>
          <label className="flex flex-col gap-xs">
            <span className="t-meta">Your name (optional)</span>
            <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
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
              autoComplete="new-password"
              required
              minLength={12}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <span className="t-small text-text-tertiary">12 characters minimum.</span>
          </label>
        </div>
        {error !== null && (
          <p className="t-small text-signal-negative">{error}</p>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create organisation"}
        </Button>
        <p className="t-small text-text-secondary">
          Already have an account?{" "}
          <a href="/login" className="underline text-text-primary">
            Sign in
          </a>
        </p>
      </form>
    </div>
  );
}
