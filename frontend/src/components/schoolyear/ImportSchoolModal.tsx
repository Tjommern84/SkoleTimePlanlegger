import { useState } from "react";
import { createPortal } from "react-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Upload, X } from "lucide-react";
import { API_BASE_URL, getActiveZoneId } from "../../api/client";

interface ImportSchoolModalProps {
  onClose: () => void;
  onImported: (schoolYearId: number) => void;
}

interface Issue {
  path: string;
  message: string;
}

interface ImportResult {
  school_year_id: number;
  counts: Record<string, number>;
  warnings: Issue[];
}

const COUNT_LABELS: Record<string, string> = {
  trinn: "trinn",
  classes: "klasser",
  class_groups: "klassegrupper",
  teachers: "lærere",
  subjects: "fag",
  activities: "aktiviteter",
};

/** FastAPI's own request-validation 422 (e.g. wrong field types) returns
 * `{"detail": [{"loc": [...], "msg": ...}]}`, distinct from our own
 * semantic-validation 422 (`{"detail": {"errors": [...], "warnings": [...]}}`).
 * Normalize both into one flat issue list for display. */
function parseErrorBody(detail: unknown): Issue[] {
  if (Array.isArray(detail)) {
    return detail.map((d: { loc?: unknown[]; msg?: string }) => ({
      path: Array.isArray(d.loc) ? d.loc.join(".") : "?",
      message: d.msg ?? "Ugyldig felt.",
    }));
  }
  if (detail && typeof detail === "object" && "errors" in detail) {
    return (detail as { errors: Issue[] }).errors;
  }
  return [{ path: "?", message: typeof detail === "string" ? detail : "Ukjent feil." }];
}

export function ImportSchoolModal({ onClose, onImported }: ImportSchoolModalProps) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [issues, setIssues] = useState<Issue[] | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);

  const submit = async () => {
    if (!file) return;
    setParseError(null);
    setIssues(null);
    setResult(null);

    let text: string;
    let parsed: unknown;
    try {
      text = await file.text();
      parsed = JSON.parse(text);
    } catch {
      setParseError("Filen er ikke gyldig JSON.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/import/school`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-Zone-Id": String(getActiveZoneId() ?? ""),
        },
        body: JSON.stringify(parsed),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) {
        setIssues(parseErrorBody(body?.detail));
        return;
      }
      setResult(body as ImportResult);
      queryClient.invalidateQueries({ queryKey: ["schoolYears"] });
    } catch {
      setIssues([{ path: "?", message: "Kunne ikke nå serveren." }]);
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">Importer fra fil</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-3 px-6 py-5">
          {!result && (
            <>
              <p className="text-xs text-ink-soft">
                Last opp en JSON-fil med et helt skoleoppsett (skoleår, trinn, klasser, lærere, fag, aktiviteter) —
                produsert f.eks. med "school-import"-skillen fra en beskrivelse av skolen.
              </p>
              <input
                type="file"
                accept="application/json"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
              />
              {parseError && <p className="text-xs text-danger">{parseError}</p>}
              {issues && (
                <div className="max-h-64 overflow-y-auto rounded-lg border border-danger-soft bg-danger-soft/30 p-3">
                  <p className="mb-1.5 text-xs font-semibold text-danger">
                    Fant {issues.length} problem{issues.length === 1 ? "" : "er"}:
                  </p>
                  <ul className="space-y-1 text-xs text-danger">
                    {issues.map((issue, i) => (
                      <li key={i}>
                        <span className="font-mono text-[11px] opacity-70">{issue.path}</span>: {issue.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {result && (
            <div className="space-y-2">
              <p className="text-sm text-ink">Import fullført.</p>
              <ul className="list-disc pl-5 text-sm text-ink-muted">
                {Object.entries(result.counts).map(([key, value]) => (
                  <li key={key}>
                    {value} {COUNT_LABELS[key] ?? key}
                  </li>
                ))}
              </ul>
              {result.warnings.length > 0 && (
                <div className="rounded-lg border border-accent-soft bg-accent-soft/40 p-3">
                  <p className="mb-1 text-xs font-semibold text-[#7a5a10]">Advarsler:</p>
                  <ul className="space-y-1 text-xs text-[#7a5a10]">
                    {result.warnings.map((w, i) => (
                      <li key={i}>{w.message}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-bg-soft"
          >
            {result ? "Lukk" : "Avbryt"}
          </button>
          {!result && (
            <button
              type="button"
              onClick={submit}
              disabled={submitting || !file}
              className="flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-60"
            >
              <Upload className="h-4 w-4" />
              {submitting ? "Importerer..." : "Last opp og importer"}
            </button>
          )}
          {result && (
            <button
              type="button"
              onClick={() => onImported(result.school_year_id)}
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark"
            >
              Gå til skoleåret
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
