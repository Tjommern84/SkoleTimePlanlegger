import { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { CheckCircle2, Download, Eye, RotateCw, Sparkles, TriangleAlert } from "lucide-react";
import { api, type SolveRequest, type SolveResponse, type VariantSummary } from "../api/client";
import { useActivities, useSubjects, useTeachers } from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { StatCard } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";

interface SolvePageProps {
  schoolYearId: number;
  onViewTimetable?: () => void;
  // Lifted up to App.tsx: the topbar's "Generer timeplan" button and this
  // page must share one solve result, not two independent mutation states.
  solve: UseMutationResult<SolveResponse, Error, SolveRequest>;
  variants: VariantSummary[];
  activeVariantId: number | null;
  lastRunAt: Date | null;
  onRunSolve: (optimize: boolean, variantCount: number) => void;
  onChooseVariant: (generatedTimetableId: number) => void;
}

const PLANNED_TOGGLES = ["Prioriter færre lærerhull", "Prioriter jevn fagfordeling"];

export function SolvePage({
  onViewTimetable,
  schoolYearId,
  solve,
  variants,
  activeVariantId,
  lastRunAt,
  onRunSolve,
  onChooseVariant,
}: SolvePageProps) {
  const subjects = useSubjects(schoolYearId);
  const teachers = useTeachers();
  const activities = useActivities(schoolYearId);
  const [optimize, setOptimize] = useState(true);
  const [generateAlternatives, setGenerateAlternatives] = useState(false);

  const warnings: string[] = [];
  if ((subjects.data?.length ?? 0) === 0) warnings.push("Ingen fag registrert");
  if ((teachers.data?.length ?? 0) === 0) warnings.push("Ingen lærere registrert");
  if ((activities.data?.length ?? 0) === 0) warnings.push("Ingen aktiviteter registrert");

  const run = () => onRunSolve(optimize, generateAlternatives ? 3 : 1);

  const isInfeasible = solve.data?.status === "INFEASIBLE";

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader title="Generer" sparkle description="Kjør løseren og kontroller resultatet." />

      <Card>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard value={activities.data?.length ?? "–"} label="Aktiviteter" />
          <StatCard value={teachers.data?.length ?? "–"} label="Lærere" />
          <StatCard value="–" label="Rom" />
          <StatCard value={12} label="Regler" />
        </div>

        <div className="mt-4 rounded-lg border border-border bg-surface-soft px-4 py-3">
          {warnings.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-success">
              <CheckCircle2 className="h-4 w-4" />
              Klar til å generere en gyldig og balansert timeplan.
            </p>
          ) : (
            <div className="space-y-1">
              {warnings.map((w) => (
                <p key={w} className="flex items-center gap-2 text-sm text-warning">
                  <TriangleAlert className="h-4 w-4" />
                  {w}
                </p>
              ))}
            </div>
          )}
        </div>

        <div className="mt-5">
          <h3 className="mb-2 text-sm font-semibold text-ink">Solver-valg</h3>
          <label className="flex items-center gap-2 py-1.5 text-sm text-ink">
            <input type="checkbox" checked={optimize} onChange={(e) => setOptimize(e.target.checked)} className="accent-primary" />
            Bruk myke regler i optimaliseringen (bl.a. matte før lunsj, KRØV-spredning)
          </label>
          <label className="flex items-center gap-2 py-1.5 text-sm text-ink">
            <input
              type="checkbox"
              checked={generateAlternatives}
              onChange={(e) => setGenerateAlternatives(e.target.checked)}
              className="accent-primary"
            />
            Generer 3 alternative varianter å velge mellom
          </label>
          {PLANNED_TOGGLES.map((label) => (
            <label key={label} className="flex items-center gap-2 py-1.5 text-sm text-ink-soft">
              <input type="checkbox" disabled className="accent-border-strong" />
              {label}
              <Badge tone="neutral">kommer snart</Badge>
            </label>
          ))}
        </div>

        <button
          type="button"
          onClick={run}
          disabled={solve.isPending}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-secondary px-4 py-3 text-sm font-semibold text-white shadow-sm transition-colors hover:opacity-90 disabled:opacity-60"
        >
          <Sparkles className="h-4 w-4" />
          {solve.isPending ? "Genererer..." : "Generer timeplan"}
        </button>
      </Card>

      {solve.data && (
        <Card className="mt-4">
          <h3 className="mb-3 text-sm font-semibold text-ink">Resultat</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatCard
              value={isInfeasible ? solve.data.infeasible_sessions.length : 0}
              label="Harde konflikter"
              tone={isInfeasible ? "danger" : "success"}
            />
            <StatCard value={isInfeasible ? 0 : solve.data.placement_count} label="Plasserte økter" tone="primary" />
            <StatCard
              value={lastRunAt ? lastRunAt.toLocaleTimeString("nb-NO", { hour: "2-digit", minute: "2-digit" }) : "–"}
              label="Sist generert"
            />
          </div>

          {isInfeasible && (
            <p className="mt-4 flex items-start gap-2 text-sm text-danger">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              Ingen gyldig timeplan funnet. Sjekk lærertilgjengelighet og aktivitetsdefinisjoner for
              motstridende krav.
            </p>
          )}

          {!isInfeasible && variants.length > 1 && (
            <div className="mt-4">
              <p className="mb-2 text-xs text-ink-muted">
                Alle {variants.length} variantene er like gyldige (samme kvalitetsscore) — de er bare
                forskjellige konkrete plasseringer. Velg den du liker best.
              </p>
              <div className="grid gap-2 sm:grid-cols-3">
                {variants.map((v, i) => (
                  <button
                    key={v.generated_timetable_id}
                    type="button"
                    onClick={() => onChooseVariant(v.generated_timetable_id)}
                    className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                      v.generated_timetable_id === activeVariantId
                        ? "border-primary bg-primary-soft text-primary-dark"
                        : "border-border bg-surface-soft text-ink hover:border-border-strong"
                    }`}
                  >
                    <span className="font-medium">Variant {i + 1}</span>
                    {v.generated_timetable_id === activeVariantId && <Badge tone="primary">Valgt</Badge>}
                    <p className="mt-0.5 text-xs text-ink-muted">{v.placement_count} økter plassert</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {!isInfeasible && onViewTimetable && (
              <button
                type="button"
                onClick={onViewTimetable}
                className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
              >
                <Eye className="h-4 w-4" />
                Vis timeplan
              </button>
            )}
            <button
              type="button"
              onClick={run}
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-sm font-medium text-ink-muted hover:text-ink"
            >
              <RotateCw className="h-4 w-4" />
              Generer ny variant
            </button>
            {!isInfeasible && activeVariantId && (
              <a
                href={api.exportUrl(activeVariantId)}
                className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-sm font-medium text-ink-muted hover:text-ink"
              >
                <Download className="h-4 w-4" />
                Last ned Excel
              </a>
            )}
          </div>
        </Card>
      )}

      {solve.isError && <p className="mt-3 text-sm text-danger">Noe gikk galt under løsing.</p>}
    </div>
  );
}
