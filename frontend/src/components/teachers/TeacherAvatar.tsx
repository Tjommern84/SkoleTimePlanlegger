const PALETTE = [
  "bg-primary-soft text-primary-dark",
  "bg-secondary-soft text-secondary",
  "bg-accent-soft text-[#8a6a1f]",
  "bg-[#F3DCE6] text-[#9A4E68]",
  "bg-[#DDEAF6] text-[#3A6E93]",
];

function colorForInitials(initials: string) {
  let hash = 0;
  for (let i = 0; i < initials.length; i++) hash = (hash * 31 + initials.charCodeAt(i)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

export function TeacherAvatar({ initials, size = "md" }: { initials: string; size?: "sm" | "md" }) {
  const sizeClasses = size === "sm" ? "h-8 w-8 text-xs" : "h-10 w-10 text-sm";
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold ${sizeClasses} ${colorForInitials(initials)}`}
    >
      {initials.slice(0, 2).toUpperCase()}
    </span>
  );
}
