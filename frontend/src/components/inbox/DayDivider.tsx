interface Props {
  label: string;
}

export function DayDivider({ label }: Props) {
  return (
    <div className="inbox-day-divider" role="separator" aria-label={label}>
      <span className="inbox-day-divider-chip">{label}</span>
    </div>
  );
}
