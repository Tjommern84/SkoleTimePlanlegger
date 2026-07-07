import { CalendarCheck2 } from "lucide-react";
import { API_BASE_URL } from "../api/client";

export function LoginPage() {
  return (
    <div className="app-background flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm rounded-lg bg-surface p-8 text-center shadow-lg">
        <span className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary-soft text-primary-dark">
          <CalendarCheck2 className="h-5 w-5" />
        </span>
        <h1 className="mt-4 text-xl font-semibold text-ink">Timeplanlegger</h1>
        <p className="mt-2 text-sm text-ink-muted">Logg inn med Google for å fortsette.</p>
        <a
          href={`${API_BASE_URL}/auth/login`}
          className="mt-6 inline-block w-full rounded-full bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-primary-dark"
        >
          Logg inn med Google
        </a>
      </div>
    </div>
  );
}
