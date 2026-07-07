import {
  BookOpen,
  Calendar,
  CalendarCheck2,
  CheckCircle2,
  Home,
  Puzzle,
  Shield,
  Sparkles,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type NavKey = "grunnoppsett" | "hours" | "teachers" | "activities" | "rules" | "solve" | "grid";

interface NavItem {
  key: NavKey;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { key: "grunnoppsett", label: "Grunnoppsett", icon: Home },
  { key: "hours", label: "Fag og timetall", icon: BookOpen },
  { key: "teachers", label: "Lærere", icon: Users },
  { key: "activities", label: "Aktiviteter", icon: Puzzle },
  { key: "rules", label: "Regler", icon: Shield },
  { key: "solve", label: "Generer", icon: Sparkles },
  { key: "grid", label: "Timeplan", icon: Calendar },
];

interface SidebarProps {
  active: NavKey;
  onNavigate: (key: NavKey) => void;
  completed: Partial<Record<NavKey, boolean>>;
}

export function Sidebar({ active, onNavigate, completed }: SidebarProps) {
  return (
    <aside
      className="flex w-[260px] shrink-0 flex-col gap-1 p-4"
      style={{
        background: "linear-gradient(180deg, var(--primary) 0%, var(--primary-dark) 100%)",
      }}
    >
      <div className="mb-6 flex items-center gap-2.5 px-2 pt-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/15 text-white">
          <CalendarCheck2 className="h-5 w-5" />
        </span>
        <span className="text-[15px] font-semibold text-white">Timeplanlegger</span>
      </div>

      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.key;
          const isDone = completed[item.key];
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onNavigate(item.key)}
              className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                isActive ? "bg-white text-primary-dark shadow-sm" : "text-white/85 hover:bg-white/10"
              }`}
            >
              <Icon className="h-4.5 w-4.5 shrink-0" />
              <span className="flex-1">{item.label}</span>
              {isDone && (
                <CheckCircle2
                  className={`h-4 w-4 shrink-0 ${isActive ? "text-success" : "text-[#8FD6A6]"}`}
                  strokeWidth={2.25}
                />
              )}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
