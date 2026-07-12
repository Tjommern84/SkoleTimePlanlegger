import { useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useCreateSchoolYear } from "../../api/hooks";

interface CreateSchoolYearModalProps {
  onClose: () => void;
  onCreated: (id: number) => void;
}

export function CreateSchoolYearModal({ onClose, onCreated }: CreateSchoolYearModalProps) {
  const [label, setLabel] = useState("");
  const createSchoolYear = useCreateSchoolYear();

  const submit = () => {
    const trimmed = label.trim();
    if (!trimmed) return;
    createSchoolYear.mutate(trimmed, { onSuccess: (year) => onCreated(year.id) });
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="w-full max-w-sm rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">Nytt skoleår</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="space-y-3 px-6 py-5">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-muted">Navn på skoleår</label>
            <input
              autoFocus
              className="w-full rounded-lg border border-border px-3 py-1.5 text-sm"
              placeholder="f.eks. 2026/2027"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          {createSchoolYear.isError && (
            <p className="text-xs text-danger">Kunne ikke opprette skoleår ({(createSchoolYear.error as Error).message}).</p>
          )}
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
            disabled={createSchoolYear.isPending || !label.trim()}
            className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-60"
          >
            Opprett
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
