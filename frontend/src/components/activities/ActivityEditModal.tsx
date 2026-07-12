import { useState } from "react";
import { createPortal } from "react-dom";
import { Plus, Trash2, X } from "lucide-react";
import type { Activity, ActivityCreate } from "../../api/client";
import { useAllClassGroups, useCreateActivity, useDeleteActivity, useSubjects, useTeachers } from "../../api/hooks";
import { SegmentedControl } from "../ui/SegmentedControl";
import { HintToggle } from "../ui/HintToggle";
import type { ActivityKind } from "./ActivityCard";

interface ActivityEditModalProps {
  schoolYearId: number;
  activity?: Activity;
  onClose: () => void;
}

interface LegForm {
  class_group_id: number | null;
  subject_id: number | null;
  teacher_ids: number[];
}

const TYPE_OPTIONS: { value: ActivityKind; label: string }[] = [
  { value: "NORMAL", label: "Normal" },
  { value: "SPLIT_PARALLEL", label: "Delt parallell" },
  { value: "TRINNFAG", label: "Trinnfag" },
];

const TYPE_HINTS: Record<ActivityKind, string> = {
  NORMAL:
    "Ett fag, én klasse(gruppe), én eller flere lærere (samundervisning). Det vanligste valget. Har alltid nøyaktig ett \"ben\". Hvis en klasse har f.eks. 3 co-underviste økter og 1 solo-økt i uken, lager du to separate Normal-aktiviteter (ulike lærerlister, ulikt antall forekomster) — ikke én aktivitet med flere ben.",
  SPLIT_PARALLEL:
    "For når en klasse deles i to halvgrupper som gjør HVER SITT fag i samme tidsrom (f.eks. halve 9A har mat og helse mens den andre halvparten har naturfag). Har alltid nøyaktig to ben — ett per halvgruppe. Skal klassen bytte fag neste økt, oppretter du en ny, separat aktivitet med benene byttet om.",
  TRINNFAG:
    "For fag som samler hele trinnet på tvers av klassene samtidig i parallelle grupper (f.eks. valgfag eller fremmedspråk med flere grupper samtidig). Ett ben per parallellgruppe. Hvis antall grupper er FLERE enn antall klasser på trinnet, sett \"Ingen hjemmeklasse\" på de ekstra benene — de opptar bare læreren, ikke en klasse.",
};

const NO_HOME_CLASS = "none";

function emptyLeg(): LegForm {
  return { class_group_id: null, subject_id: null, teacher_ids: [] };
}

function legCountForType(type: ActivityKind, current: LegForm[]): LegForm[] {
  if (type === "NORMAL") return current.length ? [current[0]] : [emptyLeg()];
  if (type === "SPLIT_PARALLEL") {
    const next = current.slice(0, 2);
    while (next.length < 2) next.push(emptyLeg());
    return next;
  }
  return current.length ? current : [emptyLeg()];
}

export function ActivityEditModal({ schoolYearId, activity, onClose }: ActivityEditModalProps) {
  const classGroups = useAllClassGroups(schoolYearId);
  const subjects = useSubjects(schoolYearId);
  const teachers = useTeachers();
  const createActivity = useCreateActivity();
  const deleteActivity = useDeleteActivity();

  const [activityType, setActivityType] = useState<ActivityKind>(
    (activity?.activity_type as ActivityKind) ?? "NORMAL",
  );
  const [showTypeHint, setShowTypeHint] = useState(false);
  const [legs, setLegs] = useState<LegForm[]>(
    activity
      ? activity.legs.map((l) => ({ class_group_id: l.class_group_id, subject_id: l.subject_id, teacher_ids: l.teacher_ids }))
      : [emptyLeg()],
  );
  const [durationMinutes, setDurationMinutes] = useState(activity ? activity.duration_ticks * 30 : 60);
  const [occurrencesPerWeek, setOccurrencesPerWeek] = useState(activity?.occurrences_per_week ?? 1);
  const [notes, setNotes] = useState(activity?.notes ?? "");

  const pending = createActivity.isPending || deleteActivity.isPending;
  const error = createActivity.error ?? deleteActivity.error;

  const changeType = (type: ActivityKind) => {
    setActivityType(type);
    setLegs((current) => legCountForType(type, current));
  };

  const updateLeg = (index: number, patch: Partial<LegForm>) => {
    setLegs((current) => current.map((leg, i) => (i === index ? { ...leg, ...patch } : leg)));
  };

  const toggleTeacher = (index: number, teacherId: number) => {
    setLegs((current) =>
      current.map((leg, i) => {
        if (i !== index) return leg;
        const has = leg.teacher_ids.includes(teacherId);
        return { ...leg, teacher_ids: has ? leg.teacher_ids.filter((id) => id !== teacherId) : [...leg.teacher_ids, teacherId] };
      }),
    );
  };

  const addLeg = () => setLegs((current) => [...current, emptyLeg()]);
  const removeLeg = (index: number) => setLegs((current) => current.filter((_, i) => i !== index));

  const isValid = legs.length > 0 && legs.every((l) => l.subject_id != null) && durationMinutes > 0 && occurrencesPerWeek > 0;
  const durationTicks = durationMinutes / 30;
  const oddTicks = Number.isInteger(durationTicks) && durationTicks % 2 !== 0;

  const submit = () => {
    if (!isValid) return;
    const payload: ActivityCreate = {
      school_year_id: schoolYearId,
      activity_type: activityType,
      duration_ticks: Math.round(durationTicks),
      occurrences_per_week: occurrencesPerWeek,
      notes: notes.trim() || undefined,
      legs: legs.map((l) => ({
        class_group_id: l.class_group_id,
        subject_id: l.subject_id as number,
        teacher_ids: l.teacher_ids,
      })),
    };
    const create = () => createActivity.mutate(payload, { onSuccess: onClose });
    if (activity) {
      // "Edit" = delete-and-recreate under the hood -- see the plan this
      // implements: an in-place PATCH would need to diff legs/teachers,
      // which is unnecessary complexity for the simple form-based editor.
      deleteActivity.mutate({ id: activity.id, schoolYearId }, { onSuccess: create });
    } else {
      create();
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">{activity ? "Rediger aktivitet" : "Ny aktivitet"}</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 px-6 py-5">
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-xs font-medium text-ink-muted">Type</label>
              <HintToggle checked={showTypeHint} onChange={setShowTypeHint} />
            </div>
            <SegmentedControl options={TYPE_OPTIONS} value={activityType} onChange={changeType} />
            {showTypeHint && (
              <p className="mt-2 text-xs leading-relaxed text-ink-soft">{TYPE_HINTS[activityType]}</p>
            )}
          </div>

          <div className="space-y-3">
            {legs.map((leg, i) => (
              <div key={i} className="rounded-lg border border-border bg-surface-soft p-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-ink-muted">Ben {i + 1}</h3>
                  {activityType === "TRINNFAG" && legs.length > 1 && (
                    <button type="button" onClick={() => removeLeg(i)} className="text-ink-soft hover:text-danger">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs text-ink-muted">Klassegruppe</label>
                    <select
                      className="w-full rounded-md border border-border px-2 py-1.5 text-sm"
                      value={leg.class_group_id ?? NO_HOME_CLASS}
                      onChange={(e) =>
                        updateLeg(i, { class_group_id: e.target.value === NO_HOME_CLASS ? null : Number(e.target.value) })
                      }
                    >
                      <option value={NO_HOME_CLASS}>Ingen hjemmeklasse (ekstra gruppe)</option>
                      {(classGroups.data ?? []).map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-ink-muted">Fag</label>
                    <select
                      className="w-full rounded-md border border-border px-2 py-1.5 text-sm"
                      value={leg.subject_id ?? ""}
                      onChange={(e) => updateLeg(i, { subject_id: e.target.value ? Number(e.target.value) : null })}
                    >
                      <option value="">Velg fag...</option>
                      {(subjects.data ?? []).map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.short_code} — {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="mt-2">
                  <label className="mb-1 block text-xs text-ink-muted">Lærer(e)</label>
                  <div className="flex flex-wrap gap-x-3 gap-y-1">
                    {(teachers.data ?? []).map((t) => (
                      <label key={t.id} className="flex items-center gap-1 text-xs text-ink">
                        <input
                          type="checkbox"
                          className="accent-primary"
                          checked={leg.teacher_ids.includes(t.id)}
                          onChange={() => toggleTeacher(i, t.id)}
                        />
                        {t.initials}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            {activityType === "TRINNFAG" && (
              <button
                type="button"
                onClick={addLeg}
                className="flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary-dark"
              >
                <Plus className="h-4 w-4" />
                Legg til ben
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted">Varighet (min)</label>
              <input
                type="number"
                min={30}
                step={30}
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(Number(e.target.value))}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-ink-muted">Forekomster/uke</label>
              <input
                type="number"
                min={1}
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                value={occurrencesPerWeek}
                onChange={(e) => setOccurrencesPerWeek(Number(e.target.value))}
              />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className="mb-1 block text-xs font-medium text-ink-muted">Notat</label>
              <input
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>
          {oddTicks && (
            <p className="text-xs text-warning">
              En enslig halvtime (30/90/... min) kan bli umulig å plassere med mindre et annet fag sin halvtime
              kan pares med den samme dagen. Vurder 60/120 min i stedet, med mindre du vet det finnes noe å pare med.
            </p>
          )}
          {error && <p className="text-xs text-danger">Kunne ikke lagre ({(error as Error).message}).</p>}
        </div>

        <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-border px-4 py-2 text-sm font-medium text-ink-muted hover:bg-bg-soft"
          >
            Avbryt
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending || !isValid}
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-60"
          >
            Lagre
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
