interface HintToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

/** A small "show explanation" checkbox meant to sit next to a section
 * heading, toggling whether that section's explanatory text is shown.
 * Defaults to unchecked (hints hidden) wherever it's used. */
export function HintToggle({ checked, onChange }: HintToggleProps) {
  return (
    <label className="flex shrink-0 items-center gap-1.5 text-xs font-normal text-ink-soft">
      <input
        type="checkbox"
        className="accent-primary"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      Vis forklaring
    </label>
  );
}
