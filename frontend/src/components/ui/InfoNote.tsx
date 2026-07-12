import type { ReactNode } from "react";

export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <div className="mb-3 rounded-lg border border-primary-soft bg-primary-soft/40 px-3 py-2.5 text-xs leading-relaxed text-primary-dark">
      {children}
    </div>
  );
}
