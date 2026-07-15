import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import type { DayOfWeek } from "../api/client";
import {
  useClasses,
  useClassGroups,
  useCreateClass,
  useCreateClassGroup,
  useCreatePeriod,
  useCreateTrinn,
  useDeleteClass,
  useDeleteClassGroup,
  useDeletePeriod,
  useDeleteSchoolYear,
  useDeleteTrinn,
  usePeriods,
  useSchoolYears,
  useTrinn,
  useUpdateClass,
  useUpdatePeriod,
  useUpdateSchoolYear,
  useUpdateTrinn,
} from "../api/hooks";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { HintToggle } from "../components/ui/HintToggle";
import { InfoNote } from "../components/ui/InfoNote";

const DAY_OPTIONS: { value: DayOfWeek; label: string }[] = [
  { value: "MON", label: "Mandag" },
  { value: "TUE", label: "Tirsdag" },
  { value: "WED", label: "Onsdag" },
  { value: "THU", label: "Torsdag" },
  { value: "FRI", label: "Fredag" },
];
const DAY_LABELS = Object.fromEntries(DAY_OPTIONS.map((d) => [d.value, d.label]));

function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return <p className="mt-1 text-xs text-danger">{(error as Error).message}</p>;
}

function SchoolYearSettings({ schoolYearId }: { schoolYearId: number }) {
  const schoolYears = useSchoolYears();
  const year = schoolYears.data?.find((y) => y.id === schoolYearId);
  const [label, setLabel] = useState(year?.label ?? "");
  const updateSchoolYear = useUpdateSchoolYear();
  const deleteSchoolYear = useDeleteSchoolYear();

  if (label === "" && year) setLabel(year.label);

  const save = () => {
    const trimmed = label.trim();
    if (trimmed && year && trimmed !== year.label) {
      updateSchoolYear.mutate({ id: schoolYearId, label: trimmed });
    }
  };

  return (
    <Card>
      <h2 className="mb-3 text-sm font-semibold text-ink">Skoleår</h2>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Navn</label>
          <input
            className="w-40 rounded-lg border border-border px-3 py-1.5 text-sm"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            onBlur={save}
          />
        </div>
        <button
          type="button"
          onClick={() => {
            const currentLabel = year?.label ?? "dette skoleåret";
            if (
              window.confirm(
                `Slette "${currentLabel}"? Dette sletter ALT under dette skoleåret permanent — trinn, klasser, fag, aktiviteter, perioder og genererte timeplaner. Kan ikke angres.`,
              )
            ) {
              deleteSchoolYear.mutate(schoolYearId, {
                onSuccess: () => window.alert(`"${currentLabel}" er slettet.`),
              });
            }
          }}
          className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm font-medium text-danger hover:bg-danger-soft"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Slett skoleår
        </button>
      </div>
      <ErrorText error={deleteSchoolYear.error} />
    </Card>
  );
}

function ClassGroupsEditor({ schoolClassId }: { schoolClassId: number }) {
  const groups = useClassGroups(schoolClassId);
  const createGroup = useCreateClassGroup();
  const deleteGroup = useDeleteClassGroup();
  const [newLabel, setNewLabel] = useState("");

  const addGroup = () => {
    const trimmed = newLabel.trim();
    if (!trimmed) return;
    createGroup.mutate({ schoolClassId, label: trimmed }, { onSuccess: () => setNewLabel("") });
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {(groups.data ?? []).map((g) => (
        <Chip key={g.id} tone={g.label === "whole" ? "neutral" : "primary"}>
          <span className="flex items-center gap-1">
            {g.label}
            <button
              type="button"
              onClick={() => deleteGroup.mutate(g.id)}
              className="text-current opacity-60 hover:opacity-100"
              title="Fjern gruppe"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </span>
        </Chip>
      ))}
      <input
        className="w-24 rounded-full border border-border px-2.5 py-1 text-xs"
        placeholder="+ delt gruppe"
        value={newLabel}
        onChange={(e) => setNewLabel(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && addGroup()}
        onBlur={addGroup}
      />
    </div>
  );
}

function ClassRow({ schoolClass, trinnId }: { schoolClass: { id: number; name: string }; trinnId: number }) {
  const [name, setName] = useState(schoolClass.name);
  const updateClass = useUpdateClass();
  const deleteClass = useDeleteClass();

  return (
    <div className="rounded-lg border border-border bg-surface-soft px-3 py-2.5">
      <div className="flex items-center gap-2">
        <input
          className="w-24 rounded-md border border-border px-2 py-1 text-sm"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => {
            const trimmed = name.trim();
            if (trimmed && trimmed !== schoolClass.name) {
              updateClass.mutate({ id: schoolClass.id, trinnId, name: trimmed });
            }
          }}
        />
        <button
          type="button"
          onClick={() => deleteClass.mutate(schoolClass.id)}
          className="ml-auto text-ink-soft hover:text-danger"
          title="Slett klasse"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
      <ErrorText error={deleteClass.error} />
      <div className="mt-2">
        <ClassGroupsEditor schoolClassId={schoolClass.id} />
      </div>
    </div>
  );
}

function TrinnRow({ trinn, schoolYearId }: { trinn: { id: number; level: number }; schoolYearId: number }) {
  const [level, setLevel] = useState(trinn.level);
  const updateTrinn = useUpdateTrinn();
  const deleteTrinn = useDeleteTrinn();
  const classes = useClasses(trinn.id);
  const createClass = useCreateClass();
  const [newClassName, setNewClassName] = useState("");

  const addClass = () => {
    const trimmed = newClassName.trim();
    if (!trimmed) return;
    createClass.mutate({ trinnId: trinn.id, name: trimmed }, { onSuccess: () => setNewClassName("") });
  };

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-ink-muted">Trinn</label>
        <input
          type="number"
          className="w-16 rounded-md border border-border px-2 py-1 text-sm"
          value={level}
          onChange={(e) => setLevel(Number(e.target.value))}
          onBlur={() => {
            if (level !== trinn.level) updateTrinn.mutate({ id: trinn.id, schoolYearId, level });
          }}
        />
        <button
          type="button"
          onClick={() => deleteTrinn.mutate(trinn.id)}
          className="ml-auto flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs font-medium text-danger hover:bg-danger-soft"
        >
          <Trash2 className="h-3 w-3" />
          Slett trinn
        </button>
      </div>
      <ErrorText error={deleteTrinn.error} />

      <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {(classes.data ?? []).map((c) => (
          <ClassRow key={c.id} schoolClass={c} trinnId={trinn.id} />
        ))}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <input
          className="w-28 rounded-lg border border-border px-3 py-1.5 text-sm"
          placeholder="Ny klasse (f.eks. 8A)"
          value={newClassName}
          onChange={(e) => setNewClassName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addClass()}
        />
        <button
          type="button"
          onClick={addClass}
          className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-sm font-medium text-ink-muted hover:bg-bg-soft"
        >
          <Plus className="h-3.5 w-3.5" />
          Legg til klasse
        </button>
      </div>
    </div>
  );
}

function TrinnSection({ schoolYearId }: { schoolYearId: number }) {
  const trinn = useTrinn(schoolYearId);
  const createTrinn = useCreateTrinn();
  const [newLevel, setNewLevel] = useState("");
  const [showHint, setShowHint] = useState(false);

  const addTrinn = () => {
    const level = Number(newLevel);
    if (!level) return;
    createTrinn.mutate({ schoolYearId, level }, { onSuccess: () => setNewLevel("") });
  };

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Trinn og klasser</h2>
        <HintToggle checked={showHint} onChange={setShowHint} />
      </div>
      {showHint && (
        <InfoNote>
          Hver klasse får automatisk en <strong>"whole"</strong>-gruppe som representerer hele klassen samlet — den
          trenger du ikke opprette selv. Bruk <strong>"+ delt gruppe"</strong> kun for klasser som noen ganger deles i
          to (f.eks. halve klassen har ett fag mens den andre halvparten har et annet samtidig). Gi de delte gruppene
          korte, konsekvente navn som "half1"/"half2" — dette er navnene du velger klassegruppe med senere når du
          setter opp aktiviteter.
        </InfoNote>
      )}
      <div className="space-y-3">
        {(trinn.data ?? [])
          .slice()
          .sort((a, b) => a.level - b.level)
          .map((t) => (
            <TrinnRow key={t.id} trinn={t} schoolYearId={schoolYearId} />
          ))}
      </div>
      <div className="mt-4 flex items-center gap-2">
        <input
          type="number"
          className="w-24 rounded-lg border border-border px-3 py-1.5 text-sm"
          placeholder="Nivå"
          value={newLevel}
          onChange={(e) => setNewLevel(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addTrinn()}
        />
        <button
          type="button"
          onClick={addTrinn}
          className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
        >
          <Plus className="h-4 w-4" />
          Legg til trinn
        </button>
      </div>
    </Card>
  );
}

interface NewPeriodForm {
  day_of_week: DayOfWeek;
  period_number: string;
  start_time: string;
  end_time: string;
  is_splittable: boolean;
  is_before_lunch: boolean;
}

const EMPTY_PERIOD_FORM: NewPeriodForm = {
  day_of_week: "MON",
  period_number: "",
  start_time: "",
  end_time: "",
  is_splittable: false,
  is_before_lunch: false,
};

function PeriodsSection({ schoolYearId }: { schoolYearId: number }) {
  const periods = usePeriods(schoolYearId);
  const createPeriod = useCreatePeriod();
  const updatePeriod = useUpdatePeriod();
  const deletePeriod = useDeletePeriod();
  const [form, setForm] = useState<NewPeriodForm>(EMPTY_PERIOD_FORM);

  const addPeriod = () => {
    const periodNumber = Number(form.period_number);
    if (!periodNumber || !form.start_time || !form.end_time) return;
    createPeriod.mutate(
      {
        school_year_id: schoolYearId,
        day_of_week: form.day_of_week,
        period_number: periodNumber,
        start_time: `${form.start_time}:00`,
        end_time: `${form.end_time}:00`,
        is_splittable: form.is_splittable,
        is_before_lunch: form.is_before_lunch,
      },
      { onSuccess: () => setForm(EMPTY_PERIOD_FORM) },
    );
  };

  const [showHint, setShowHint] = useState(false);

  const sorted = (periods.data ?? [])
    .slice()
    .sort((a, b) => DAY_OPTIONS.findIndex((d) => d.value === a.day_of_week) - DAY_OPTIONS.findIndex((d) => d.value === b.day_of_week) || a.period_number - b.period_number);

  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">Perioder (ukeplan)</h2>
        <HintToggle checked={showHint} onChange={setShowHint} />
      </div>
      {showHint && (
        <InfoNote>
          Dette er selve grunnmuren timeplanen bygges på — legg til én rad per periode, per dag skolen faktisk har
          undervisning. En dag uten lagte perioder blir automatisk en fridag/kort dag for solveren (du trenger f.eks.
          ikke legge inn periode 5–6 på en dag som slutter tidlig).
          <br />
          <strong>Splittbar (halvtime)</strong>: kryss av hvis perioden kan deles i to 30-minutters økter (nyttig for
          fag med brøkdels-timetall). To splittbare perioder samme dag kan også slås sammen til én 60-minutters økt.
          En enslig 30-minutters økt uten noe å pares med i samme periode er umulig å plassere.
          <br />
          <strong>Før lunsj</strong>: brukes av myke regler som "Matematikk bør ligge før lunsj" (se Regler-siden) — merk
          av på alle periodene som faktisk ligger før lunsjpausen.
        </InfoNote>
      )}
      {sorted.length > 0 && (
        <div className="mb-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs font-semibold text-ink-muted">
                <th className="p-1.5">Dag</th>
                <th className="p-1.5">Periode</th>
                <th className="p-1.5">Start</th>
                <th className="p-1.5">Slutt</th>
                <th className="p-1.5">Splittbar</th>
                <th className="p-1.5">Før lunsj</th>
                <th className="p-1.5" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => (
                <tr key={p.id} className="border-t border-border">
                  <td className="p-1.5">{DAY_LABELS[p.day_of_week]}</td>
                  <td className="p-1.5">{p.period_number}</td>
                  <td className="p-1.5">
                    <input
                      type="time"
                      className="rounded-md border border-border px-1.5 py-1 text-xs"
                      defaultValue={p.start_time.slice(0, 5)}
                      onBlur={(e) =>
                        updatePeriod.mutate({
                          id: p.id,
                          payload: { ...p, start_time: `${e.target.value}:00` },
                        })
                      }
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="time"
                      className="rounded-md border border-border px-1.5 py-1 text-xs"
                      defaultValue={p.end_time.slice(0, 5)}
                      onBlur={(e) =>
                        updatePeriod.mutate({
                          id: p.id,
                          payload: { ...p, end_time: `${e.target.value}:00` },
                        })
                      }
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="checkbox"
                      checked={p.is_splittable}
                      onChange={(e) =>
                        updatePeriod.mutate({ id: p.id, payload: { ...p, is_splittable: e.target.checked } })
                      }
                    />
                  </td>
                  <td className="p-1.5">
                    <input
                      type="checkbox"
                      checked={p.is_before_lunch}
                      onChange={(e) =>
                        updatePeriod.mutate({ id: p.id, payload: { ...p, is_before_lunch: e.target.checked } })
                      }
                    />
                  </td>
                  <td className="p-1.5">
                    <button
                      type="button"
                      onClick={() => deletePeriod.mutate(p.id)}
                      className="text-ink-soft hover:text-danger"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 rounded-lg bg-bg-soft p-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Dag</label>
          <select
            className="rounded-lg border border-border px-2 py-1.5 text-sm"
            value={form.day_of_week}
            onChange={(e) => setForm({ ...form, day_of_week: e.target.value as DayOfWeek })}
          >
            {DAY_OPTIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Periodenr.</label>
          <input
            type="number"
            className="w-20 rounded-lg border border-border px-2 py-1.5 text-sm"
            value={form.period_number}
            onChange={(e) => setForm({ ...form, period_number: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Start</label>
          <input
            type="time"
            className="rounded-lg border border-border px-2 py-1.5 text-sm"
            value={form.start_time}
            onChange={(e) => setForm({ ...form, start_time: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-ink-muted">Slutt</label>
          <input
            type="time"
            className="rounded-lg border border-border px-2 py-1.5 text-sm"
            value={form.end_time}
            onChange={(e) => setForm({ ...form, end_time: e.target.value })}
          />
        </div>
        <label className="flex items-center gap-1.5 pb-2 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={form.is_splittable}
            onChange={(e) => setForm({ ...form, is_splittable: e.target.checked })}
          />
          Splittbar (halvtime)
        </label>
        <label className="flex items-center gap-1.5 pb-2 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={form.is_before_lunch}
            onChange={(e) => setForm({ ...form, is_before_lunch: e.target.checked })}
          />
          Før lunsj
        </label>
        <button
          type="button"
          onClick={addPeriod}
          className="flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-sm font-medium text-white hover:bg-primary-dark"
        >
          <Plus className="h-4 w-4" />
          Legg til periode
        </button>
      </div>
      <ErrorText error={createPeriod.error} />
      <ErrorText error={updatePeriod.error} />
      <ErrorText error={deletePeriod.error} />
    </Card>
  );
}

export function GrunnoppsettPage({ schoolYearId }: { schoolYearId: number }) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Grunnoppsett"
        description="Skoleår, trinn, klasser og periodeoppsett (ringetider, lunsj, halvtimer)."
      />
      <SchoolYearSettings schoolYearId={schoolYearId} />
      <TrinnSection schoolYearId={schoolYearId} />
      <PeriodsSection schoolYearId={schoolYearId} />
    </div>
  );
}
