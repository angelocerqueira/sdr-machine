interface KbdProps {
  children: React.ReactNode;
  className?: string;
}

export function Kbd({ children, className = "" }: KbdProps) {
  return (
    <kbd
      className={`inline-flex items-center justify-center h-[18px] min-w-[18px] px-1 text-[10px] font-mono text-text-muted border border-border-strong bg-surface rounded-xs ${className}`}
    >
      {children}
    </kbd>
  );
}
