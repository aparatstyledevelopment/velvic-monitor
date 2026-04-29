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
        display_name: displayName || undefined,
        password,
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
    <div className="min-h-full flex items-center justify-center px-lg">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-[360px] flex flex-col gap-lg"
        aria-labelledby="signup-title"
      >
        <h1 id="signup-title" className="t-title">Create your organisation</h1>
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
        {error && <p className="t-small" style={{ color: "var(--signal-negative)" }}>{error}</p>}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create organisation"}
        </Button>
        <p className="t-small">
          Already have an account?{" "}
          <a href="/login" className="underline">
            Sign in
          </a>
        </p>
      </form>
    </div>
  );
}
