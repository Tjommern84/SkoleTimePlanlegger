import { useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import type { Subject, SubjectCreate } from "../../api/client";
import { useCreateSubject, useUpdateSubject } from "../../api/hooks";
import { HintToggle } from "../ui/HintToggle";

interface SubjectEditModalProps {
  schoolYearId: number;
  subject?: Subject;
  onClose: () => void;
}

const FLAG_FIELDS: { key: keyof SubjectCreate; label: string; hint: string }[] = [
  {
    key: "is_trinnfag",
    label: "Trinnfag",
    hint:
      "Bruk dette for fag som samler HELE trinnet på tvers av klasser samtidig, f.eks. valgfag eller fremmedspråk (flere parallelle grupper går samtidig, ikke fag-for-fag per klasse). Slå dette på hvis faget skal opprettes som en TRINNFAG-aktivitet med flere \"ben\" (én per parallellgruppe) i Aktiviteter-siden.",
  },
  {
    key: "is_krov",
    label: "KRØV (kroppsøving)",
    hint:
      "Merk kroppsøving/gym-fag med dette. Det gjør at faget telles mot skolens grense for hvor mange klasser som kan ha kroppsøving samtidig (typisk fordi det bare finnes én gymsal/hall) — se \"Maks 2 samtidige KRØV-økter\" på Regler-siden.",
  },
  {
    key: "uses_hall",
    label: "Bruker hall",
    hint:
      "Slå på for fag som fysisk opptar hallen/gymsalen (f.eks. et valgfag med idrettsaktivitet). Mens et slikt fag pågår, blokkeres ALL kroppsøving for hele skolen — ikke bare for den ene klassen. Vanlige fag (som fremmedspråk) skal IKKE ha dette flagget selv om de er trinnfag, siden de ikke bruker hallen.",
  },
  {
    key: "avoid_consecutive",
    label: "Unngå sammenhengende økter",
    hint:
      "En myk preferanse for fag som ikke bør ligge i to perioder på rad samme dag, f.eks. musikk. Solveren prøver å unngå dette, men vil tillate det hvis timeplanen ellers ikke går opp.",
  },
  {
    key: "prefer_before_lunch",
    label: "Bør ligge før lunsj",
    hint:
      "En myk preferanse for fag som helst bør legges tidlig på dagen, f.eks. matematikk. Ikke et hardt krav — kan brytes ved behov.",
  },
  {
    key: "needs_consecutive_periods",
    label: "Trenger sammenhengende perioder",
    hint:
      "For praktiske fag som trenger 2 (eller flere) perioder rett etter hverandre for å gi mening, f.eks. mat og helse eller kunst og håndverk — en enkeltperiode holder ikke til å faktisk gjennomføre timen.",
  },
];

const EMPTY: SubjectCreate = {
  school_year_id: 0,
  name: "",
  short_code: "",
  is_trinnfag: false,
  is_krov: false,
  uses_hall: false,
  avoid_consecutive: false,
  prefer_before_lunch: false,
  needs_consecutive_periods: false,
};

export function SubjectEditModal({ schoolYearId, subject, onClose }: SubjectEditModalProps) {
  const [form, setForm] = useState<SubjectCreate>(subject ?? { ...EMPTY, school_year_id: schoolYearId });
  const [showHints, setShowHints] = useState(false);
  const createSubject = useCreateSubject();
  const updateSubject = useUpdateSubject();
  const pending = createSubject.isPending || updateSubject.isPending;
  const error = createSubject.error ?? updateSubject.error;

  const submit = () => {
    if (!form.name.trim() || !form.short_code.trim()) return;
    if (subject) {
      updateSubject.mutate({ id: subject.id, payload: form }, { onSuccess: onClose });
    } else {
      createSubject.mutate(form, { onSuccess: onClose });
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">{subject ? "Rediger fag" : "Nytt fag"}</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-medium text-ink-muted">Navn</label>
              <input
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="w-28">
              <label className="mb-1 block text-xs font-medium text-ink-muted">Kortkode</label>
              <input
                className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
                value={form.short_code}
                onChange={(e) => setForm({ ...form, short_code: e.target.value.toUpperCase() })}
              />
            </div>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink">Egenskaper</h3>
              <HintToggle checked={showHints} onChange={setShowHints} />
            </div>
            <div className="space-y-2">
              {FLAG_FIELDS.map((f) => (
                <label key={f.key} className="flex items-start gap-2 text-sm text-ink">
                  <input
                    type="checkbox"
                    className="mt-0.5 accent-primary"
                    checked={Boolean(form[f.key])}
                    onChange={(e) => setForm({ ...form, [f.key]: e.target.checked })}
                  />
                  <span>
                    {f.label}
                    {showHints && <span className="block text-xs text-ink-soft">{f.hint}</span>}
                  </span>
                </label>
              ))}
            </div>
          </div>

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
            disabled={pending || !form.name.trim() || !form.short_code.trim()}
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
