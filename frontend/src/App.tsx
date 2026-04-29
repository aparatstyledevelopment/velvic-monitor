import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { authApi } from "./api/auth";
import { ApiError } from "./api/client";
import { LoginPage } from "./auth/LoginPage";
import { SignupPage } from "./auth/SignupPage";
import { AppShell } from "./layout/AppShell";
import { DriversModule } from "./modules/drivers/DriversModule";
import { useAuth } from "./state/auth";

export function App() {
  const me = useAuth((s) => s.me);
  const loading = useAuth((s) => s.loading);
  const setMe = useAuth((s) => s.setMe);
  const setLoading = useAuth((s) => s.setLoading);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const fresh = await authApi.me();
        if (!cancelled) setMe(fresh);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 401)) {
          // unexpected; surface in console for now, Sentry in Phase 5
          console.error("auth/me failed", err);
        }
        if (!cancelled) setMe(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [setMe, setLoading]);

  useEffect(() => {
    if (loading) return;
    const isAuthRoute = location.pathname === "/login" || location.pathname === "/signup";
    if (!me && !isAuthRoute) navigate("/login", { replace: true });
    if (me && isAuthRoute) navigate("/", { replace: true });
  }, [loading, me, location.pathname, navigate]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center t-small text-text-tertiary">
        Loading…
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/"
        element={
          <AppShell>
            <DriversModule />
          </AppShell>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
