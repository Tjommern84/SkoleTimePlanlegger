import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { api, type Teacher } from "../api/client";
import { useCreateTeacher, useDeleteTeacher, useTeachers, useTeacherUnavailabilities } from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { TeacherAvatar } from "../components/teachers/TeacherAvatar";
import { TeacherEditModal } from "../components/teachers/TeacherEditModal";

interface TeacherRowProps {
  teacher: Teacher;
  subjectCodes: string[];
  weeklyHours: number;
  onEdit: () => void;
}

function TeacherRow({ teacher, subjectCodes, weeklyHours, onEdit }: TeacherRowProps) {
  const unavailabilities = useTeacherUnavailabilities(teacher.id);
  const deleteTeacher = useDeleteTeacher();
  const nameKnown = teacher.full_name && teacher.full_name !== teacher.initials;

  return (
    <tr className="border-t border-border">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <TeacherAvatar initials={teacher.initials} />
          <div>
            <p className="font-medium text-ink">{nameKnown ? teacher.full_name : teacher.initials}</p>
            <p className="text-xs text-ink-soft">{teacher.initials}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {subjectCodes.length > 0 ? (
            subjectCodes.map((code) => <Chip key={code}>{code}</Chip>)
          ) : (
            <span className="text-xs text-ink-soft">–</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-ink">{weeklyHours > 0 ? `${weeklyHours} t/uke` : "–"}</td>
      <td className="px-4 py-3 text-xs text-ink-muted">
        {unavailabilities.isLoading
          ? "…"
          : unavailabilities.data && unavailabilities.data.length > 0
            ? `${unavailabilities.data.length} blokkerte økt${unavailabilities.data.length === 1 ? "" : "er"}`
            : "Ingen"}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="flex items-center gap-1 rounded-full px-2.5 py-1.5 text-xs font-medium text-ink-muted hover:bg-primary-soft hover:text-primary-dark"
            title="Rediger lærer"
          >
            <Pencil className="h-3.5 w-3.5" />
            Rediger
          </button>
          <button
            type="button"
            onClick={() => {
              if (confirm(`Fjerne ${teacher.initials}?`)) deleteTeacher.mutate(teacher.id);
            }}
            className="rounded-full p-1.5 text-ink-soft hover:bg-danger-soft hover:text-danger"
            title="Fjern lærer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

export function TeachersPage({ schoolYearId }: { schoolYearId: number }) {
  const teachers = useTeachers();
  const createTeacher = useCreateTeacher();
  const activities = useQuery({
    queryKey: ["activities", schoolYearId],
    queryFn: () => api.activities.list(schoolYearId),
  });
  const subjects = useQuery({ queryKey: ["subjects", schoolYearId], queryFn: () => api.subjects.list(schoolYearId) });
  const subjectById = Object.fromEntries((subjects.data ?? []).map((s) => [s.id, s]));

  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [initials, setInitials] = useState("");
  const [fullName, setFullName] = useState("");
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null);

  const subjectCodesByTeacher: Record<number, Set<string>> = {};
  const hoursByTeacher: Record<number, number> = {};
  for (const a of activities.data ?? []) {
    for (const leg of a.legs) {
      const subject = subjectById[leg.subject_id];
      // Each co-teacher is present for the whole session, so each gets the
      // full hours credited -- not split between them. Splitting was
      // undercounting real teaching load whenever a teacher co-taught.
      const hours = a.occurrences_per_week * a.duration_ticks * 0.5;
      for (const teacherId of leg.teacher_ids) {
        subjectCodesByTeacher[teacherId] = subjectCodesByTeacher[teacherId] ?? new Set();
        if (subject) subjectCodesByTeacher[teacherId].add(subject.short_code);
        hoursByTeacher[teacherId] = (hoursByTeacher[teacherId] ?? 0) + hours;
      }
    }
  }

  const filtered = (teachers.data ?? []).filter((t) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return t.initials.toLowerCase().includes(q) || t.full_name.toLowerCase().includes(q);
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!initials.trim() || !fullName.trim()) return;
    createTeacher.mutate(
      { initials: initials.trim(), fullName: fullName.trim() },
      {
        onSuccess: () => {
          setInitials("");
          setFullName("");
          setShowForm(false);
        },
      },
    );
  };

  return (
    <div>
      <PageHeader
        title="Lærere"
        description="Administrer lærere, initialer, fagtilknytning og tilgjengelighet."
        actions={
          <button
            type="button"
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
          >
            <Plus className="h-4 w-4" />
            Legg til lærer
          </button>
        }
      />

      {showForm && (
        <Card className="mb-5">
          <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted">Initialer</label>
              <input
                className="rounded-lg border border-border px-3 py-1.5 text-sm"
                placeholder="F.eks. GB"
                value={initials}
                onChange={(e) => setInitials(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-ink-muted">Fullt navn</label>
              <input
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                placeholder="Valgfritt"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <button
              type="submit"
              disabled={createTeacher.isPending}
              className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-60"
            >
              Lagre
            </button>
          </form>
        </Card>
      )}

      <div className="mb-4">
        <div className="relative max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-soft" />
          <input
            className="w-full rounded-full border border-border bg-surface py-2 pr-3 pl-9 text-sm shadow-sm"
            placeholder="Søk etter lærer..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {teachers.isError && <p className="text-sm text-danger">Kunne ikke laste lærere.</p>}

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-soft text-xs font-semibold text-ink-muted uppercase">
                <th className="px-4 py-3">Lærer</th>
                <th className="px-4 py-3">Fag</th>
                <th className="px-4 py-3 text-right">Timer</th>
                <th className="px-4 py-3">Utilgjengelighet</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {teachers.isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-ink-muted">
                    Laster...
                  </td>
                </tr>
              )}
              {filtered.map((t) => (
                <TeacherRow
                  key={t.id}
                  teacher={t}
                  subjectCodes={[...(subjectCodesByTeacher[t.id] ?? [])].sort()}
                  weeklyHours={Math.round((hoursByTeacher[t.id] ?? 0) * 10) / 10}
                  onEdit={() => setEditingTeacher(t)}
                />
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {editingTeacher && (
        <TeacherEditModal
          teacher={editingTeacher}
          schoolYearId={schoolYearId}
          subjects={subjects.data ?? []}
          onClose={() => setEditingTeacher(null)}
        />
      )}
    </div>
  );
}
