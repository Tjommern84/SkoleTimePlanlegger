export type Tone = "neutral" | "primary" | "secondary" | "accent" | "success" | "warning" | "danger";

export const toneClasses: Record<Tone, string> = {
  neutral: "bg-bg-soft text-ink-muted",
  primary: "bg-primary-soft text-primary-dark",
  secondary: "bg-secondary-soft text-secondary",
  accent: "bg-accent-soft text-[#8a6a1f]",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
};
