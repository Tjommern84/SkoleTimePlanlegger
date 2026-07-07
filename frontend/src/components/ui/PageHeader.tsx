import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";

interface PageHeaderProps {
  title: string;
  description?: string;
  sparkle?: boolean;
  actions?: ReactNode;
}

export function PageHeader({ title, description, sparkle, actions }: PageHeaderProps) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold text-ink">
          {title}
          {sparkle && <Sparkles className="h-5 w-5 text-accent" strokeWidth={2} />}
        </h1>
        {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
