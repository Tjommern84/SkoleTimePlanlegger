import { useState } from "react";
import {
  useActivateVariant,
  useActiveTimetable,
  useActivities,
  useMe,
  useSchoolYears,
  useSolve,
  useSubjects,
  useTeachers,
} from "./api/hooks";
import type { VariantSummary } from "./api/client";
import { LoginPage } from "./pages/LoginPage";
import { TeachersPage } from "./pages/TeachersPage";
import { SubjectHoursPage } from "./pages/SubjectHoursPage";
import { ActivitiesPage } from "./pages/ActivitiesPage";
import { SolvePage } from "./pages/SolvePage";
import { TimetableGridPage } from "./pages/TimetableGridPage";
import { RulesPage } from "./pages/RulesPage";
import { GrunnoppsettPage } from "./pages/GrunnoppsettPage";
import { AppShell } from "./components/layout/AppShell";
import { Sidebar, type NavKey } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import type { Tone } from "./components/ui/tone";

function Dashboard() {
  const me = useMe();
  const [nav, setNav] = useState<NavKey>("hours");
  const schoolYears = useSchoolYears();
  const [schoolYearId, setSchoolYearId] = useState<number | null>(null);

  const years = schoolYears.data ?? [];
  if (schoolYearId === null && years.length > 0) {
    setSchoolYearId(years[0].id);
  }

  const subjects = useSubjects(schoolYearId ?? undefined);
  const teachers = useTeachers();
  const activities = useActivities(schoolYearId ?? undefined);
  const activeTimetable = useActiveTimetable(schoolYearId ?? undefined);

  // Solve state is lifted here (rather than living inside SolvePage) so the
  // topbar's "Generer timeplan" button and the Generer page's own button
  // share the same result -- two separate useSolve() instances would each
  // have independent mutation state and silently disagree about what the
  // last solve produced.
  const solve = useSolve();
  const activateVariant = useActivateVariant(schoolYearId ?? 0);
  const [variants, setVariants] = useState<VariantSummary[]>([]);
  const [activeVariantId, setActiveVariantId] = useState<number | null>(null);
  const [lastRunAt, setLastRunAt] = useState<Date | null>(null);

  const runSolve = (optimize: boolean, variantCount: number) => {
    if (schoolYearId === null) return;
    solve.mutate(
      { school_year_id: schoolYearId, time_limit_seconds: 60, optimize, variant_count: variantCount },
      {
        onSuccess: (data) => {
          setVariants(data.variants);
          setActiveVariantId(data.variants[0]?.generated_timetable_id ?? data.generated_timetable_id ?? null);
          setLastRunAt(new Date());
        },
      },
    );
  };

  const chooseVariant = (id: number) => {
    activateVariant.mutate(id, {
      onSuccess: () => {
        setActiveVariantId(id);
        setVariants((prev) => prev.map((v) => ({ ...v, is_active: v.generated_timetable_id === id })));
      },
    });
  };

  const statusInfo: { label: string; tone: Tone } = activeTimetable.data
    ? activeTimetable.data.solver_status === "INFEASIBLE"
      ? { label: "Konflikter", tone: "danger" }
      : { label: "Gyldig plan", tone: "success" }
    : { label: "Utkast lagret", tone: "secondary" };

  const completed: Partial<Record<NavKey, boolean>> = {
    hours: (subjects.data?.length ?? 0) > 0,
    teachers: (teachers.data?.length ?? 0) > 0,
    activities: (activities.data?.length ?? 0) > 0,
  };

  return (
    <AppShell
      sidebar={<Sidebar active={nav} onNavigate={setNav} completed={completed} />}
      topbar={
        <Topbar
          schoolYears={years}
          schoolYearId={schoolYearId}
          onSchoolYearChange={setSchoolYearId}
          statusLabel={statusInfo.label}
          statusTone={statusInfo.tone}
          userEmail={me.data?.email}
          generating={solve.isPending}
          onGenerate={() => runSolve(true, 1)}
        />
      }
    >
      {schoolYearId === null ? (
        <p className="text-sm text-ink-muted">Ingen skoleår funnet.</p>
      ) : (
        <>
          {nav === "grunnoppsett" && <GrunnoppsettPage schoolYearId={schoolYearId} />}
          {nav === "hours" && <SubjectHoursPage schoolYearId={schoolYearId} />}
          {nav === "teachers" && <TeachersPage schoolYearId={schoolYearId} />}
          {nav === "activities" && <ActivitiesPage schoolYearId={schoolYearId} />}
          {nav === "rules" && <RulesPage />}
          {nav === "solve" && (
            <SolvePage
              schoolYearId={schoolYearId}
              onViewTimetable={() => setNav("grid")}
              solve={solve}
              variants={variants}
              activeVariantId={activeVariantId}
              lastRunAt={lastRunAt}
              onRunSolve={runSolve}
              onChooseVariant={chooseVariant}
            />
          )}
          {nav === "grid" && <TimetableGridPage schoolYearId={schoolYearId} />}
        </>
      )}
    </AppShell>
  );
}

function App() {
  const me = useMe();

  if (me.isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-ink-muted">Laster...</div>;
  }
  if (!me.data) {
    return <LoginPage />;
  }
  return <Dashboard />;
}

export default App;
