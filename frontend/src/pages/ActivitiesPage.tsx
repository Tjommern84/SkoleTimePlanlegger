import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api } from "../api/client";
import { useActivities, useAllClassGroups, type ClassGroupInfo } from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ActivityCard, type ActivityKind } from "../components/activities/ActivityCard";

const TYPE_LABELS: Record<ActivityKind, string> = {
  NORMAL: "Normal",
  SPLIT_PARALLEL: "Delt klasse",
  TRINNFAG: "Trinnfag",
};

export function ActivitiesPage({ schoolYearId }: { schoolYearId: number }) {
  const activities = useActivities(schoolYearId);
  const subjects = useQuery({ queryKey: ["subjects", schoolYearId], queryFn: () => api.subjects.list(schoolYearId) });
  const teachers = useQuery({ queryKey: ["teachers"], queryFn: api.teachers.list });
  const classGroups = useAllClassGroups(schoolYearId);

  const [trinnFilter, setTrinnFilter] = useState<string>("all");
  const [subjectFilter, setSubjectFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const subjectById = Object.fromEntries((subjects.data ?? []).map((s) => [s.id, s]));
  const teacherById = Object.fromEntries((teachers.data ?? []).map((t) => [t.id, t]));
  const classGroupById = Object.fromEntries((classGroups.data ?? []).map((g) => [g.id, g]));

  function trinnOf(legs: { class_group_id: number | null }[]): number | null {
    for (const leg of legs) {
      if (leg.class_group_id !== null) {
        const g = classGroupById[leg.class_group_id] as ClassGroupInfo | undefined;
        if (g) return g.trinnLevel;
      }
    }
    return null;
  }

  const filtered = (activities.data ?? []).filter((a) => {
    const trinn = trinnOf(a.legs);
    if (trinnFilter !== "all" && String(trinn) !== trinnFilter) return false;
    if (typeFilter !== "all" && a.activity_type !== typeFilter) return false;
    if (subjectFilter !== "all" && !a.legs.some((l) => String(l.subject_id) === subjectFilter)) return false;
    return true;
  });

  const groupsByTrinn: Record<string, typeof filtered> = {};
  for (const a of filtered) {
    const trinn = trinnOf(a.legs);
    const key = trinn ? `${trinn}. trinn` : "Uten trinn";
    groupsByTrinn[key] = groupsByTrinn[key] ?? [];
    groupsByTrinn[key].push(a);
  }
  const grouped = Object.entries(groupsByTrinn).sort(([a], [b]) => a.localeCompare(b, "nb"));

  return (
    <div>
      <PageHeader
        title="Aktiviteter"
        description="Ukentlig gjentakende mønstre (fag × klasse(r) × lærer(e)), gruppert per trinn."
        actions={
          <button
            type="button"
            title="Redigeringsgrensesnitt for aktivitetsmatrisen kommer i en senere versjon"
            className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white opacity-60"
          >
            <Plus className="h-4 w-4" />
            Ny aktivitet
          </button>
        }
      />

      <div className="mb-5 flex flex-wrap gap-2">
        <select
          className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-ink shadow-sm"
          value={trinnFilter}
          onChange={(e) => setTrinnFilter(e.target.value)}
        >
          <option value="all">Alle trinn</option>
          <option value="8">8. trinn</option>
          <option value="9">9. trinn</option>
          <option value="10">10. trinn</option>
        </select>
        <select
          className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-ink shadow-sm"
          value={subjectFilter}
          onChange={(e) => setSubjectFilter(e.target.value)}
        >
          <option value="all">Alle fag</option>
          {(subjects.data ?? []).map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        <select
          className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm text-ink shadow-sm"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="all">Alle typer</option>
          <option value="NORMAL">Normal</option>
          <option value="SPLIT_PARALLEL">Delt klasse</option>
          <option value="TRINNFAG">Trinnfag</option>
        </select>
      </div>

      {activities.isLoading && <p className="text-sm text-ink-muted">Laster...</p>}

      {!activities.isLoading && filtered.length === 0 && (
        <Card>
          <EmptyState title="Ingen aktiviteter matcher filteret" description="Prøv å endre eller nullstille filtrene over." />
        </Card>
      )}

      <div className="space-y-6">
        {grouped.map(([groupName, items]) => (
          <Card key={groupName}>
            <h2 className="mb-3 text-sm font-semibold text-ink">
              {groupName} <span className="font-normal text-ink-soft">({items.length})</span>
            </h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((a) => {
                const lines = a.legs.map((leg) => {
                  const subject = subjectById[leg.subject_id];
                  const teacherNames = leg.teacher_ids.map((id) => teacherById[id]?.initials ?? id).join("/");
                  const classLabel = leg.class_group_id
                    ? (classGroupById[leg.class_group_id]?.label ?? `gruppe #${leg.class_group_id}`)
                    : "Ekstra parallellgruppe, ingen hjemmeklasse";
                  return `${classLabel} — ${subject?.short_code ?? leg.subject_id} (${teacherNames})`;
                });
                return (
                  <ActivityCard
                    key={a.id}
                    title={a.notes ?? `Aktivitet ${a.id}`}
                    lines={lines}
                    kind={a.activity_type as ActivityKind}
                    occurrenceLabel={`${TYPE_LABELS[a.activity_type as ActivityKind]} · ${a.occurrences_per_week} × ${a.duration_ticks * 30} min`}
                  />
                );
              })}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
