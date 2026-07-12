import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api, type Activity } from "../api/client";
import { useActivities, useAllClassGroups, useDeleteActivity, type ClassGroupInfo } from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { HintToggle } from "../components/ui/HintToggle";
import { InfoNote } from "../components/ui/InfoNote";
import { ActivityCard, type ActivityKind } from "../components/activities/ActivityCard";
import { ActivityEditModal } from "../components/activities/ActivityEditModal";

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
  const [editingActivity, setEditingActivity] = useState<Activity | "new" | null>(null);
  const [showHint, setShowHint] = useState(false);
  const deleteActivity = useDeleteActivity();

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
            onClick={() => setEditingActivity("new")}
            className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
          >
            <Plus className="h-4 w-4" />
            Ny aktivitet
          </button>
        }
      />

      <Card className="mb-5">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Hva er en "aktivitet"?</h2>
          <HintToggle checked={showHint} onChange={setShowHint} />
        </div>
        {showHint && (
          <InfoNote>
            <p>
              En aktivitet er ett <strong>ukentlig gjentakende undervisningsmønster</strong>: ett fag, én eller flere
              klasse(grupper), én eller flere lærere, hvor lenge økten varer, og hvor mange ganger i uken den skjer.
              Solveren plasserer deretter hver aktivitet i timeplanen basert på disse opplysningene.
            </p>
            <p className="mt-2">
              Hver aktivitet består av ett eller flere <strong>"ben"</strong> — ett ben er én kombinasjon av
              klassegruppe + fag + lærer(e) som skjer i akkurat det samme tidsrommet som de andre bena i aktiviteten.
              Hvor mange ben du trenger avhenger av typen:
            </p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>
                <strong>Normal</strong> (vanligst): ett ben — én klasse(gruppe), ett fag, én eller flere lærere
                (samundervisning). Eksempel: "8A har norsk med lærer GB". Har klassen f.eks. 3 co-underviste
                norsktimer og 1 solo-time i uken, oppretter du <strong>to separate</strong> Normal-aktiviteter (ulikt
                antall forekomster og ulik lærerliste) — ikke én aktivitet med to ben.
              </li>
              <li>
                <strong>Delt parallell</strong>: nøyaktig to ben. Brukes når en klasse deles i to halvgrupper som gjør
                hvert sitt fag <strong>samtidig</strong>. Eksempel: halve 9A har mat og helse mens den andre
                halvparten har naturfag, i akkurat samme periode. Skal gruppene bytte fag en annen økt i uken, lager
                du en ny, egen aktivitet for det bytte.
              </li>
              <li>
                <strong>Trinnfag</strong>: ett ben per parallellgruppe (kan være mange). Brukes når hele trinnet
                samles i valgfrie/parallelle grupper på tvers av klassene samtidig, f.eks. valgfag eller
                fremmedspråk. Har trinnet flere grupper enn klasser, setter du klassegruppe til
                "Ingen hjemmeklasse" på de ekstra bena — de opptar da bare læreren, ikke en klasse.
              </li>
            </ul>
            <p className="mt-2">
              Listen under viser aktivitetene som allerede er opprettet, gruppert per trinn — bruk filtrene for å
              finne igjen en bestemt aktivitet, og "Ny aktivitet"-knappen øverst for å opprette en ny.
            </p>
          </InfoNote>
        )}
      </Card>

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
                    onEdit={() => setEditingActivity(a)}
                    onDelete={() => {
                      if (confirm("Slette denne aktiviteten?")) {
                        deleteActivity.mutate({ id: a.id, schoolYearId });
                      }
                    }}
                  />
                );
              })}
            </div>
          </Card>
        ))}
      </div>

      {editingActivity && (
        <ActivityEditModal
          schoolYearId={schoolYearId}
          activity={editingActivity === "new" ? undefined : editingActivity}
          onClose={() => setEditingActivity(null)}
        />
      )}
    </div>
  );
}
