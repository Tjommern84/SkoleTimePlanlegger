import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { api, type Subject } from "../api/client";
import {
  useCreateSubjectHourAllocation,
  useDeleteSubject,
  useUpdateSubjectHourAllocation,
} from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { StatCard } from "../components/ui/StatCard";
import { Chip } from "../components/ui/Chip";
import { SubjectEditModal } from "../components/subjects/SubjectEditModal";

function HourCell({
  subjectId,
  trinnId,
  schoolYearId,
  allocationId,
  weeklyHours,
}: {
  subjectId: number;
  trinnId: number;
  schoolYearId: number;
  allocationId: number | undefined;
  weeklyHours: number | undefined;
}) {
  const qc = useQueryClient();
  const [value, setValue] = useState(weeklyHours != null ? String(weeklyHours) : "");
  const createAllocation = useCreateSubjectHourAllocation();
  const updateAllocation = useUpdateSubjectHourAllocation();

  const invalidate = () => qc.invalidateQueries({ queryKey: ["subjectHourTable", schoolYearId] });

  const save = () => {
    const trimmed = value.trim();
    const hours = trimmed === "" ? null : Number(trimmed);
    if (hours === null || Number.isNaN(hours)) return;
    if (allocationId != null) {
      if (hours !== weeklyHours) {
        updateAllocation.mutate(
          { id: allocationId, payload: { subject_id: subjectId, trinn_id: trinnId, weekly_hours: hours } },
          { onSuccess: invalidate },
        );
      }
    } else {
      createAllocation.mutate(
        { subject_id: subjectId, trinn_id: trinnId, weekly_hours: hours },
        { onSuccess: invalidate },
      );
    }
  };

  return (
    <input
      type="number"
      min={0}
      step={0.5}
      className="w-16 rounded-md border border-border px-1.5 py-1 text-right text-sm tabular-nums"
      placeholder="–"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      onBlur={save}
    />
  );
}

export function SubjectHoursPage({ schoolYearId }: { schoolYearId: number }) {
  const qc = useQueryClient();
  const trinn = useQuery({
    queryKey: ["trinn", schoolYearId],
    queryFn: () => api.trinn.list(schoolYearId),
  });
  const subjects = useQuery({
    queryKey: ["subjects", schoolYearId],
    queryFn: () => api.subjects.list(schoolYearId),
  });
  const deleteSubject = useDeleteSubject();

  const table = useQuery({
    queryKey: ["subjectHourTable", schoolYearId, subjects.data?.map((s) => s.id).join(",")],
    queryFn: async () => {
      if (!subjects.data) return {};
      const entries = await Promise.all(
        subjects.data.map(async (s) => [s.id, await api.subjects.hourAllocations(s.id)] as const),
      );
      return Object.fromEntries(entries);
    },
    enabled: !!subjects.data,
  });

  const [editingSubject, setEditingSubject] = useState<Subject | "new" | null>(null);

  const levels = [...(trinn.data ?? [])].sort((a, b) => a.level - b.level);

  const totalByTrinn: Record<number, number> = {};
  for (const allocations of Object.values(table.data ?? {})) {
    for (const a of allocations as { trinn_id: number; weekly_hours: number }[]) {
      totalByTrinn[a.trinn_id] = (totalByTrinn[a.trinn_id] ?? 0) + Number(a.weekly_hours);
    }
  }

  return (
    <div>
      <PageHeader
        title="Fag og timetall"
        description="Definer uketimer og egenskaper for hvert fag på hvert trinn."
        actions={
          <button
            type="button"
            onClick={() => setEditingSubject("new")}
            className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
          >
            <Plus className="h-4 w-4" />
            Nytt fag
          </button>
        }
      />

      {levels.length > 0 && (
        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {levels.map((t) => (
            <StatCard key={t.id} value={`${totalByTrinn[t.id] ?? "–"} t`} label={`${t.level}. trinn`} tone="primary" />
          ))}
        </div>
      )}

      <Card padding="none" className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-surface-soft text-xs font-semibold text-ink-muted uppercase">
                <th className="px-4 py-3">Fag</th>
                {levels.map((t) => (
                  <th key={t.id} className="px-4 py-3 text-right">
                    {t.level}. trinn
                  </th>
                ))}
                <th className="px-4 py-3">Egenskaper</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {(subjects.isLoading || trinn.isLoading) && (
                <tr>
                  <td colSpan={levels.length + 3} className="px-4 py-6 text-center text-ink-muted">
                    Laster...
                  </td>
                </tr>
              )}
              {subjects.data?.map((s) => {
                const allocations = table.data?.[s.id] ?? [];
                return (
                  <tr key={s.id} className="border-t border-border">
                    <td className="px-4 py-3 font-medium text-ink">
                      {s.name} <span className="text-ink-soft">({s.short_code})</span>
                    </td>
                    {levels.map((t) => {
                      const alloc = allocations.find((a: { trinn_id: number }) => a.trinn_id === t.id);
                      return (
                        <td key={t.id} className="px-4 py-3 text-right">
                          <HourCell
                            subjectId={s.id}
                            trinnId={t.id}
                            schoolYearId={schoolYearId}
                            allocationId={alloc?.id}
                            weeklyHours={alloc?.weekly_hours}
                          />
                        </td>
                      );
                    })}
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {s.prefer_before_lunch && <Chip tone="success">før lunsj</Chip>}
                        {s.uses_hall && <Chip tone="primary">bruker hall</Chip>}
                        {s.is_trinnfag && <Chip tone="accent">trinnfag</Chip>}
                        {s.avoid_consecutive && <Chip tone="warning">unngå sammenhengende</Chip>}
                        {s.needs_consecutive_periods && <Chip tone="secondary">praktisk fag</Chip>}
                        {s.is_krov && <Chip tone="secondary">KRØV</Chip>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setEditingSubject(s)}
                          className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft"
                          title="Rediger fag"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteSubject.mutate(s.id, { onSuccess: () => qc.invalidateQueries({ queryKey: ["subjectHourTable", schoolYearId] }) })}
                          className="rounded-full p-1.5 text-ink-soft hover:bg-danger-soft hover:text-danger"
                          title="Slett fag"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {deleteSubject.isError && (
          <p className="px-4 py-2 text-xs text-danger">
            Kunne ikke slette faget ({(deleteSubject.error as Error).message}).
          </p>
        )}
      </Card>

      {editingSubject && (
        <SubjectEditModal
          schoolYearId={schoolYearId}
          subject={editingSubject === "new" ? undefined : editingSubject}
          onClose={() => setEditingSubject(null)}
        />
      )}
    </div>
  );
}
