import { AlertTriangle, Lock } from "lucide-react";
import { getSubjectStyle } from "../../lib/subjectStyle";

interface LessonCardProps {
  subjectName: string;
  subjectCode: string;
  teacherLabel?: string;
  conflict?: boolean;
  locked?: boolean;
}

export function LessonCard({ subjectName, subjectCode, teacherLabel, conflict, locked }: LessonCardProps) {
  const style = getSubjectStyle(subjectCode);
  const Icon = style.icon;

  return (
    <div
      className={`flex h-full flex-col gap-1 rounded-md border px-2.5 py-2 text-left ${
        conflict ? "border-danger" : "border-transparent"
      }`}
      style={{ backgroundColor: conflict ? "var(--danger-soft)" : style.bg }}
    >
      <div className="flex items-center justify-between gap-1">
        <Icon className="h-3.5 w-3.5 shrink-0" style={{ color: conflict ? "var(--danger)" : style.text }} />
        <div className="flex items-center gap-1">
          {locked && <Lock className="h-3 w-3 text-ink-soft" />}
          {conflict && <AlertTriangle className="h-3 w-3 text-danger" />}
        </div>
      </div>
      <div>
        <p className="text-xs leading-tight font-semibold" style={{ color: conflict ? "var(--danger)" : style.text }}>
          {subjectName}
        </p>
        <p className="text-[11px] leading-tight" style={{ color: conflict ? "var(--danger)" : style.text, opacity: 0.75 }}>
          {subjectCode}
          {teacherLabel ? ` · ${teacherLabel}` : ""}
        </p>
      </div>
    </div>
  );
}
