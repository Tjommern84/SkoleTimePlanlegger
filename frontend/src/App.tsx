import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
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
import { setActiveZoneId, type VariantSummary, type ZoneSummary } from "./api/client";
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
import { CreateSchoolYearModal } from "./components/schoolyear/CreateSchoolYearModal";
import type { Tone } from "./components/ui/tone";

interface DashboardProps {
  zones: ZoneSummary[];
  activeZoneId: number;
  onZoneChange: (id: number) => void;
}

function Dashboard({ zones, activeZoneId, onZoneChange }: DashboardProps) {
  const me = useMe();
  const [nav, setNav] = useState<NavKey>("hours");
  const schoolYears = useSchoolYears();
  const [schoolYearId, setSchoolYearId] = useState<number | null>(null);
  const [creatingSchoolYear, setCreatingSchoolYear] = useState(false);

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
          zones={zones}
          activeZoneId={activeZoneId}
          onZoneChange={onZoneChange}
          onCreateSchoolYear={() => setCreatingSchoolYear(true)}
        />
      }
    >
      {schoolYearId === null ? (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <p className="text-sm text-ink-muted">Ingen skoleår funnet ennå.</p>
          <button
            type="button"
            onClick={() => setCreatingSchoolYear(true)}
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark"
          >
            Opprett skoleår
          </button>
        </div>
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
      {creatingSchoolYear && (
        <CreateSchoolYearModal
          onClose={() => setCreatingSchoolYear(false)}
          onCreated={(id) => {
            setSchoolYearId(id);
            setCreatingSchoolYear(false);
          }}
        />
      )}
    </AppShell>
  );
}

const ACTIVE_ZONE_STORAGE_KEY = "activeZoneId";

/** Sits between the login gate and Dashboard: picks which zone the user is
 * currently working in (most users only ever have one) before any
 * zone-scoped data (school years, teachers, ...) is fetched. */
function ZoneGate({ zones }: { zones: ZoneSummary[] }) {
  const queryClient = useQueryClient();
  // Set synchronously during the lazy useState initializer (which runs
  // during render, before Dashboard's children mount) rather than in a
  // useEffect -- React commits child effects before parent effects, so an
  // effect here would fire AFTER Dashboard's own useSchoolYears/useTeachers
  // queries had already gone out with no X-Zone-Id header at all.
  const [activeZoneId, setActiveZoneIdState] = useState<number>(() => {
    const stored = Number(localStorage.getItem(ACTIVE_ZONE_STORAGE_KEY));
    const initial = zones.some((z) => z.id === stored) ? stored : zones[0].id;
    setActiveZoneId(initial);
    localStorage.setItem(ACTIVE_ZONE_STORAGE_KEY, String(initial));
    return initial;
  });

  const handleZoneChange = (id: number) => {
    queryClient.clear();
    setActiveZoneId(id);
    localStorage.setItem(ACTIVE_ZONE_STORAGE_KEY, String(id));
    setActiveZoneIdState(id);
  };

  return <Dashboard zones={zones} activeZoneId={activeZoneId} onZoneChange={handleZoneChange} />;
}

function App() {
  const me = useMe();

  if (me.isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-ink-muted">Laster...</div>;
  }
  if (!me.data) {
    return <LoginPage />;
  }
  if (me.data.zones.length === 0) {
    // Shouldn't normally happen (a zone is auto-provisioned on login), but
    // could occur if the user was just removed from their only zone.
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-ink-muted">
        Du har ikke tilgang til noen sone lenger.
      </div>
    );
  }
  return <ZoneGate zones={me.data.zones} />;
}

export default App;
