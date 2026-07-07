import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, StickyNote, X } from "lucide-react";
import { API_BASE_URL, type Subject, type Teacher } from "../../api/client";
import {
  useAddTeacherQualification,
  useAddTeacherUnavailability,
  useRemoveTeacherQualification,
  useRemoveTeacherUnavailability,
  useTeacherQualifications,
  useTeacherUnavailabilities,
  useUpdateTeacher,
  useUpdateTeacherQualification,
} from "../../api/hooks";
import type { PeriodInfo } from "../../lib/grid";

const DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI"] as const;
const DAY_LABELS: Record<string, string> = {
  MON: "Man",
  TUE: "Tir",
  WED: "Ons",
  THU: "Tor",
  FRI: "Fre",
};

function Note({ tone, icon, children }: { tone: "info" | "reminder"; icon: React.ReactNode; children: React.ReactNode }) {
  const classes =
    tone === "info" ? "border-primary-soft bg-primary-soft/40 text-primary-dark" : "border-accent-soft bg-accent-soft/50 text-[#7a5a10]";
  return (
    <div className={`flex gap-2 rounded-lg border px-3 py-2.5 text-xs leading-relaxed ${classes}`}>
      <span className="mt-0.5 shrink-0">{icon}</span>
      <span>{children}</span>
    </div>
  );
}

interface TeacherEditModalProps {
  teacher: Teacher;
  schoolYearId: number;
  subjects: Subject[];
  onClose: () => void;
}

export function TeacherEditModal({ teacher, schoolYearId, subjects, onClose }: TeacherEditModalProps) {
  const [initials, setInitials] = useState(teacher.initials);
  const [fullName, setFullName] = useState(teacher.full_name);
  const updateTeacher = useUpdateTeacher();

  const qualifications = useTeacherQualifications(teacher.id);
  const addQualification = useAddTeacherQualification(teacher.id);
  const updateQualification = useUpdateTeacherQualification(teacher.id);
  const removeQualification = useRemoveTeacherQualification(teacher.id);

  const unavailabilities = useTeacherUnavailabilities(teacher.id);
  const addUnavailability = useAddTeacherUnavailability(teacher.id);
  const removeUnavailability = useRemoveTeacherUnavailability(teacher.id);

  const periods = useQuery<PeriodInfo[]>({
    queryKey: ["periods", schoolYearId],
    queryFn: () =>
      fetch(`${API_BASE_URL}/api/periods?school_year_id=${schoolYearId}`, { credentials: "include" }).then((r) =>
        r.json(),
      ),
  });
  const maxPeriodByDay: Record<string, number> = {};
  for (const p of periods.data ?? []) {
    maxPeriodByDay[p.day_of_week] = Math.max(maxPeriodByDay[p.day_of_week] ?? 0, p.period_number);
  }
  const maxPeriods = Math.max(0, ...Object.values(maxPeriodByDay));

  const qualificationBySubject = Object.fromEntries((qualifications.data ?? []).map((q) => [q.subject_id, q]));

  const blockedCell = (day: string, period: number) =>
    (unavailabilities.data ?? []).find(
      (u) =>
        u.day_of_week === day &&
        (u.start_period === null || u.start_period === undefined
          ? true
          : period >= u.start_period! && period <= (u.end_period ?? u.start_period!)),
    );

  const saveName = () => {
    if (initials.trim() && fullName.trim() && (initials !== teacher.initials || fullName !== teacher.full_name)) {
      updateTeacher.mutate({ id: teacher.id, initials: initials.trim(), fullName: fullName.trim() });
    }
  };

  const toggleSubject = (subject: Subject, checked: boolean) => {
    if (checked) {
      addQualification.mutate({ subjectId: subject.id, weeklyHours: null });
    } else {
      const existing = qualificationBySubject[subject.id];
      if (existing) removeQualification.mutate(existing.id);
    }
  };

  const toggleCell = (day: string, period: number) => {
    const existing = blockedCell(day, period);
    if (existing) {
      removeUnavailability.mutate(existing.id);
    } else {
      addUnavailability.mutate({
        teacher_id: teacher.id,
        school_year_id: schoolYearId,
        day_of_week: day as never,
        start_period: period,
        end_period: period,
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">Rediger lærer</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 px-6 py-5">
          {/* Navn */}
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink">Navn</h3>
            <div className="flex gap-2">
              <div className="w-28">
                <label className="mb-1 block text-xs font-medium text-ink-muted">Initialer</label>
                <input
                  className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                  value={initials}
                  onChange={(e) => setInitials(e.target.value)}
                  onBlur={saveName}
                />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-ink-muted">Fullt navn</label>
                <input
                  className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  onBlur={saveName}
                />
              </div>
            </div>
          </div>

          {/* Fag */}
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink">Fag læreren kan undervise</h3>
            <Note tone="info" icon={<Info className="h-3.5 w-3.5" />}>
              Dette er en enkel oversikt over hvilke fag læreren kan undervise, og et omtrentlig antall timer i uken
              per fag. Det er <strong>ikke</strong> det som setter opp selve timeplanen — hvem som faktisk underviser
              hvilken klasse styres fortsatt fra Aktiviteter-siden. Tenk på denne listen som en enkel CV for læreren,
              ikke fagfordelingen.
            </Note>
            <Note tone="reminder" icon={<StickyNote className="h-3.5 w-3.5" />}>
              <strong>Huskelapp (utvikler):</strong> Avhukingen her lagres i en egen, enkel tabell
              (<code>teacher_subject_qualifications</code>) og påvirker ikke solveren. Når aktivitetsmatrise-editoren
              bygges, bør vi vurdere om denne listen skal kobles til/erstattes av den, slik at fagtilknytning kun
              trenger å registreres ett sted.
            </Note>
            <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
              {subjects.map((s) => {
                const qualification = qualificationBySubject[s.id];
                const checked = !!qualification;
                return (
                  <div key={s.id} className="flex items-center gap-2">
                    <label className="flex flex-1 items-center gap-2 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => toggleSubject(s, e.target.checked)}
                        className="accent-primary"
                      />
                      {s.short_code}
                    </label>
                    {checked && (
                      <input
                        type="number"
                        min={0}
                        step={0.5}
                        className="w-14 rounded-md border border-border px-1.5 py-0.5 text-right text-xs"
                        placeholder="t/uke"
                        defaultValue={qualification.weekly_hours ?? ""}
                        onBlur={(e) => {
                          const v = e.target.value === "" ? null : Number(e.target.value);
                          updateQualification.mutate({ id: qualification.id, weeklyHours: v });
                        }}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Utilgjengelighet */}
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink">Utilgjengelighet</h3>
            <Note tone="info" icon={<Info className="h-3.5 w-3.5" />}>
              Dette er et <strong>ukentlig gjentakende</strong> mønster (f.eks. "alltid opptatt mandag periode 1-3"),
              ikke spesifikke kalenderdatoer som ved ferie-booking. Klikk på en rute for å markere at læreren aldri
              kan undervise i den perioden, uansett hvilken uke det er.
            </Note>
            <Note tone="reminder" icon={<StickyNote className="h-3.5 w-3.5" />}>
              <strong>Huskelapp (utvikler):</strong> Ekte fraværsperioder med datoer (f.eks. en konkret ferieuke) er
              ikke støttet ennå — kun det ukentlige mønsteret. Vurder en egen "unntak fra dato til dato"-modell hvis
              skolen trenger det senere.
            </Note>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr>
                    <th className="w-10 p-1" />
                    {DAY_ORDER.map((day) => (
                      <th key={day} className="p-1 text-center font-semibold text-ink-muted">
                        {DAY_LABELS[day]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: maxPeriods }, (_, i) => i + 1).map((period) => (
                    <tr key={period}>
                      <td className="p-1 text-center font-medium text-ink-soft">{period}</td>
                      {DAY_ORDER.map((day) => {
                        const dayMax = maxPeriodByDay[day] ?? 0;
                        if (period > dayMax) return <td key={day} className="p-1" />;
                        const blocked = !!blockedCell(day, period);
                        return (
                          <td key={day} className="p-1">
                            <button
                              type="button"
                              onClick={() => toggleCell(day, period)}
                              className={`h-7 w-full rounded-md border transition-colors ${
                                blocked
                                  ? "border-danger bg-danger-soft"
                                  : "border-border bg-surface-soft hover:border-border-strong"
                              }`}
                              title={blocked ? "Opptatt — klikk for å fjerne" : "Ledig — klikk for å blokkere"}
                            />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="flex justify-end border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark"
          >
            Lukk
          </button>
        </div>
      </div>
    </div>
  );
}
