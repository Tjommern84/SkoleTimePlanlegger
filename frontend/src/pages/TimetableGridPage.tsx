import { Fragment, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Settings2, ShieldAlert, UtensilsCrossed } from "lucide-react";
import { api, API_BASE_URL } from "../api/client";
import { useActiveTimetable, useActivities, useAllClassGroups, useTeachers } from "../api/hooks";
import { dayTickToPeriod, touchedPeriods, type PeriodInfo } from "../lib/grid";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { SegmentedControl } from "../components/ui/SegmentedControl";
import { Chip } from "../components/ui/Chip";
import { EmptyState } from "../components/ui/EmptyState";
import { LessonCard } from "../components/grid/LessonCard";

const DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI"] as const;
const DAY_LABELS: Record<string, string> = {
  MON: "Mandag",
  TUE: "Tirsdag",
  WED: "Onsdag",
  THU: "Torsdag",
  FRI: "Fredag",
};

interface Lesson {
  subjectCode: string;
  subjectName: string;
  label: string; // teacher initials (class view) or class name (teacher view)
}

type ViewMode = "class" | "teacher" | "subject" | "room";

export function TimetableGridPage({ schoolYearId }: { schoolYearId: number }) {
  const [viewMode, setViewMode] = useState<ViewMode>("class");
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [selectedTeacherId, setSelectedTeacherId] = useState<number | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | null>(null);

  const trinn = useQuery({ queryKey: ["trinn", schoolYearId], queryFn: () => api.trinn.list(schoolYearId) });
  const classesQuery = useQuery({
    queryKey: ["allClasses", schoolYearId, trinn.data?.map((t) => t.id).join(",")],
    queryFn: async () => {
      if (!trinn.data) return [];
      const lists = await Promise.all(trinn.data.map((t) => api.classes.list(t.id)));
      return lists.flat();
    },
    enabled: !!trinn.data,
  });
  const classGroups = useAllClassGroups(schoolYearId);
  const classGroupsForSelectedClass = useMemo(
    () => (classGroups.data ?? []).filter((g) => classesQuery.data?.find((c) => c.id === selectedClassId)?.name === g.className),
    [classGroups.data, classesQuery.data, selectedClassId],
  );

  const periods = useQuery<PeriodInfo[]>({
    queryKey: ["periods", schoolYearId],
    queryFn: () =>
      fetch(`${API_BASE_URL}/api/periods?school_year_id=${schoolYearId}`, { credentials: "include" }).then((r) =>
        r.json(),
      ),
  });

  const activities = useActivities(schoolYearId);
  const activeTimetable = useActiveTimetable(schoolYearId);
  const subjects = useQuery({ queryKey: ["subjects", schoolYearId], queryFn: () => api.subjects.list(schoolYearId) });
  const teachers = useTeachers();

  const classes = classesQuery.data ?? [];
  if (selectedClassId === null && classes.length > 0) {
    setSelectedClassId(classes[0].id);
  }
  if (selectedTeacherId === null && (teachers.data?.length ?? 0) > 0) {
    setSelectedTeacherId(teachers.data![0].id);
  }
  if (selectedSubjectId === null && (subjects.data?.length ?? 0) > 0) {
    setSelectedSubjectId(subjects.data![0].id);
  }

  const maxPeriodByDay = useMemo(() => {
    const map: Record<string, number> = {};
    for (const p of periods.data ?? []) {
      map[p.day_of_week] = Math.max(map[p.day_of_week] ?? 0, p.period_number);
    }
    return map;
  }, [periods.data]);

  const periodTimeLabel = useMemo(() => {
    const map: Record<string, string> = {};
    for (const p of periods.data ?? []) {
      map[`${p.day_of_week}:${p.period_number}`] = `${p.start_time.slice(0, 5)} – ${p.end_time.slice(0, 5)}`;
    }
    return map;
  }, [periods.data]);

  const lunchTimeLabel = useMemo(() => {
    const monday = (periods.data ?? []).filter((p) => p.day_of_week === "MON").sort((a, b) => a.period_number - b.period_number);
    const before = monday.filter((p) => p.is_before_lunch).pop();
    const after = monday.find((p) => !p.is_before_lunch);
    if (!before || !after) return null;
    return `${before.end_time.slice(0, 5)} – ${after.start_time.slice(0, 5)}`;
  }, [periods.data]);

  const tickToPeriodByDay = useMemo(() => {
    const map: Record<string, number[]> = {};
    for (const day of DAY_ORDER) {
      map[day] = dayTickToPeriod((periods.data ?? []).filter((p) => p.day_of_week === day));
    }
    return map;
  }, [periods.data]);

  const cellLessons = useMemo(() => {
    const result: Record<string, Lesson[]> = {};
    if (!activeTimetable.data || !activities.data || !subjects.data || !teachers.data) return result;

    const activityById = Object.fromEntries(activities.data.map((a) => [a.id, a]));
    const subjectById = Object.fromEntries(subjects.data.map((s) => [s.id, s]));
    const teacherById = Object.fromEntries(teachers.data.map((t) => [t.id, t]));
    const classGroupLabelById = Object.fromEntries((classGroups.data ?? []).map((g) => [g.id, g.label]));
    const myGroupIds = new Set(classGroupsForSelectedClass.map((g) => g.id));

    for (const slot of activeTimetable.data.slots) {
      const activity = activityById[slot.activity_id];
      if (!activity) continue;

      const relevantLegs =
        viewMode === "class"
          ? activity.legs.filter((leg) => leg.class_group_id !== null && myGroupIds.has(leg.class_group_id))
          : viewMode === "subject"
            ? activity.legs.filter((leg) => leg.subject_id === selectedSubjectId)
            : activity.legs.filter((leg) => leg.teacher_ids.includes(selectedTeacherId ?? -1));
      if (relevantLegs.length === 0) continue;

      const periodsTouched = touchedPeriods(tickToPeriodByDay[slot.day_of_week] ?? [], slot.start_tick, slot.duration_ticks);
      for (const leg of relevantLegs) {
        const subject = subjectById[leg.subject_id];
        const label =
          viewMode === "class"
            ? leg.teacher_ids.map((id) => teacherById[id]?.initials ?? String(id)).join("/")
            : viewMode === "subject"
              ? ((leg.class_group_id ? classGroupLabelById[leg.class_group_id] : null) ?? "Ekstra gruppe") +
                (leg.teacher_ids.length
                  ? ` · ${leg.teacher_ids.map((id) => teacherById[id]?.initials ?? String(id)).join("/")}`
                  : "")
              : (leg.class_group_id ? classGroupLabelById[leg.class_group_id] : null) ?? "Ekstra gruppe";
        const lesson: Lesson = { subjectCode: subject?.short_code ?? "?", subjectName: subject?.name ?? "?", label };
        for (const period of periodsTouched) {
          const key = `${slot.day_of_week}:${period}`;
          result[key] = result[key] ?? [];
          if (!result[key].some((l) => l.subjectCode === lesson.subjectCode && l.label === lesson.label)) {
            result[key].push(lesson);
          }
        }
      }
    }
    return result;
  }, [
    activeTimetable.data,
    activities.data,
    subjects.data,
    teachers.data,
    classGroups.data,
    classGroupsForSelectedClass,
    tickToPeriodByDay,
    viewMode,
    selectedTeacherId,
    selectedSubjectId,
  ]);

  const maxPeriods = Math.max(0, ...Object.values(maxPeriodByDay));
  const beforeLunchPeriods = (periods.data ?? []).filter((p) => p.day_of_week === "MON" && p.is_before_lunch);
  const lunchAfterPeriod = beforeLunchPeriods.length
    ? Math.max(...beforeLunchPeriods.map((p) => p.period_number))
    : null;

  return (
    <div>
      <PageHeader
        title="Timeplan"
        sparkle
        description={
          viewMode === "class"
            ? "Viser timeplan for valgt klasse."
            : viewMode === "teacher"
              ? "Viser timeplan for valgt lærer."
              : viewMode === "subject"
                ? "Viser hvilke klasser som har valgt fag i hver periode -- nyttig for å sjekke at f.eks. KRØV ikke havner i for mange klasser samtidig."
                : "Rom er ikke registrert i systemet ennå."
        }
        actions={
          <>
            <button
              type="button"
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-sm font-medium text-ink-muted hover:text-ink"
              title="Solver-innstillinger kommer i en senere versjon"
            >
              <Settings2 className="h-4 w-4" />
              Innstillinger
            </button>
            <button
              type="button"
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-3.5 py-2 text-sm font-medium text-ink-muted hover:text-ink"
              title="Den genererte planen har allerede blitt kontrollert for harde konflikter av solveren"
            >
              <ShieldAlert className="h-4 w-4" />
              Vis konflikter
            </button>
          </>
        }
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-ink-muted">Vis som</span>
          <SegmentedControl
            value={viewMode}
            onChange={setViewMode}
            options={[
              { value: "class", label: "Klasse" },
              { value: "teacher", label: "Lærer" },
              { value: "subject", label: "Fag" },
              { value: "room", label: "Rom" },
            ]}
          />
        </div>

        {viewMode === "class" && (
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-ink shadow-sm"
            value={selectedClassId ?? ""}
            onChange={(e) => setSelectedClassId(Number(e.target.value))}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        )}
        {viewMode === "teacher" && (
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-ink shadow-sm"
            value={selectedTeacherId ?? ""}
            onChange={(e) => setSelectedTeacherId(Number(e.target.value))}
          >
            {(teachers.data ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.initials}
              </option>
            ))}
          </select>
        )}
        {viewMode === "subject" && (
          <select
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm font-medium text-ink shadow-sm"
            value={selectedSubjectId ?? ""}
            onChange={(e) => setSelectedSubjectId(Number(e.target.value))}
          >
            {(subjects.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.short_code} — {s.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {viewMode === "room" ? (
        <Card>
          <EmptyState
            title="Rom er ikke i bruk ennå"
            description="Datamodellen sporer ikke rom/klasserom i denne versjonen av Timeplanlegger."
          />
        </Card>
      ) : activeTimetable.isError ? (
        <Card>
          <EmptyState
            title="Ingen generert timeplan ennå"
            description="Gå til Generer-siden og trykk «Generer timeplan» for å lage en plan."
          />
        </Card>
      ) : activeTimetable.data ? (
        <Card padding="none" className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] table-fixed border-collapse text-sm">
              <thead>
                <tr>
                  <th className="w-20 border-b border-border bg-surface-soft p-3 text-left text-xs font-semibold text-ink-muted uppercase">
                    Periode
                  </th>
                  {DAY_ORDER.map((day) => (
                    <th
                      key={day}
                      className="border-b border-border bg-surface-soft p-3 text-left text-xs font-semibold text-ink-muted uppercase"
                    >
                      {DAY_LABELS[day]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Array.from({ length: maxPeriods }, (_, i) => i + 1).map((period) => (
                  <Fragment key={period}>
                    <tr>
                      <td className="border-b border-border p-2 align-top">
                        <div className="font-semibold text-ink">{period}</div>
                        <div className="text-[11px] text-ink-soft">{periodTimeLabel[`MON:${period}`]}</div>
                      </td>
                      {DAY_ORDER.map((day) => {
                        const dayMax = maxPeriodByDay[day] ?? 0;
                        if (period > dayMax) {
                          return <td key={day} className="border-b border-border bg-bg-soft/40 p-2" />;
                        }
                        const lessons = cellLessons[`${day}:${period}`] ?? [];
                        return (
                          <td key={day} className="border-b border-border p-1.5 align-top">
                            <div className="flex flex-col gap-1">
                              {lessons.map((lesson, i) => (
                                <LessonCard
                                  key={i}
                                  subjectCode={lesson.subjectCode}
                                  subjectName={lesson.subjectName}
                                  teacherLabel={lesson.label}
                                />
                              ))}
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                    {period === lunchAfterPeriod && (
                      <tr>
                        <td colSpan={DAY_ORDER.length + 1} className="border-b border-border bg-warning-soft/50 px-3 py-2">
                          <div className="flex items-center justify-center gap-2 text-xs font-medium text-ink-muted">
                            <UtensilsCrossed className="h-3.5 w-3.5" />
                            Lunsj{lunchTimeLabel ? ` · ${lunchTimeLabel}` : ""}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <Card>
          <p className="text-sm text-ink-muted">Laster...</p>
        </Card>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Chip tone="accent">Trinnfag</Chip>
        <Chip tone="secondary">Valgfag</Chip>
        <Chip tone="warning">Praktisk</Chip>
        <Chip tone="danger">Språk</Chip>
        <Chip tone="success">Før lunsj</Chip>
        <Chip tone="primary">Bruker hall</Chip>
      </div>
    </div>
  );
}
