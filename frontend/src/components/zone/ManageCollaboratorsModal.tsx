import { useState } from "react";
import { createPortal } from "react-dom";
import { Trash2, X } from "lucide-react";
import {
  useCreateInvitation,
  useRemoveMember,
  useRevokeInvitation,
  useZoneInvitations,
  useZoneMembers,
} from "../../api/hooks";

interface ManageCollaboratorsModalProps {
  isOwner: boolean;
  onClose: () => void;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Venter",
  accepted: "Akseptert",
  revoked: "Trukket tilbake",
};

export function ManageCollaboratorsModal({ isOwner, onClose }: ManageCollaboratorsModalProps) {
  const [email, setEmail] = useState("");
  const members = useZoneMembers();
  const invitations = useZoneInvitations(isOwner);
  const createInvitation = useCreateInvitation();
  const revokeInvitation = useRevokeInvitation();
  const removeMember = useRemoveMember();

  const pendingInvitations = (invitations.data ?? []).filter((i) => i.status === "pending");

  const sendInvitation = () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    createInvitation.mutate(trimmed, { onSuccess: () => setEmail("") });
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-ink">Del sonen</h2>
          <button type="button" onClick={onClose} className="rounded-full p-1.5 text-ink-soft hover:bg-bg-soft">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 px-6 py-5">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink">Medlemmer</h3>
            <ul className="space-y-1.5">
              {(members.data ?? []).map((m) => (
                <li key={m.user_id} className="flex items-center justify-between rounded-md bg-bg-soft px-3 py-1.5 text-sm">
                  <div>
                    <span className="text-ink">{m.name}</span>{" "}
                    <span className="text-ink-soft">({m.email})</span>{" "}
                    <span className="text-xs font-medium text-ink-muted">
                      {m.role === "owner" ? "eier" : "medlem"}
                    </span>
                  </div>
                  {isOwner && m.role !== "owner" && (
                    <button
                      type="button"
                      onClick={() => removeMember.mutate(m.user_id)}
                      className="text-ink-soft hover:text-danger"
                      title="Fjern medlem"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {isOwner && (
            <div>
              <h3 className="mb-2 text-sm font-semibold text-ink">Inviter noen med Google-konto</h3>
              <div className="flex gap-2">
                <input
                  type="email"
                  className="flex-1 rounded-lg border border-border px-3 py-1.5 text-sm"
                  placeholder="navn@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendInvitation()}
                />
                <button
                  type="button"
                  onClick={sendInvitation}
                  disabled={createInvitation.isPending}
                  className="rounded-lg bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-dark disabled:opacity-60"
                >
                  Inviter
                </button>
              </div>
              {createInvitation.isError && (
                <p className="mt-1.5 text-xs text-danger">
                  Kunne ikke invitere ({(createInvitation.error as Error).message}).
                </p>
              )}
              <p className="mt-1.5 text-xs text-ink-soft">
                Personen legges automatisk til neste gang de logger inn med akkurat denne Google-kontoen.
              </p>

              {pendingInvitations.length > 0 && (
                <ul className="mt-3 space-y-1.5">
                  {pendingInvitations.map((inv) => (
                    <li key={inv.id} className="flex items-center justify-between rounded-md bg-bg-soft px-3 py-1.5 text-sm">
                      <span className="text-ink">
                        {inv.email} <span className="text-xs text-ink-soft">({STATUS_LABELS[inv.status]})</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => revokeInvitation.mutate(inv.id)}
                        className="text-ink-soft hover:text-danger"
                        title="Trekk tilbake invitasjon"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
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
    </div>,
    document.body,
  );
}
