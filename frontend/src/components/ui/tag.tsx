import { Icon, type IconName } from "./icon";

interface TagProps {
  children: React.ReactNode;
  icon?: IconName;
  className?: string;
}

export function Tag({ children, icon, className = "" }: TagProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 h-[22px] px-2 text-xs font-mono text-text-muted border border-border rounded-xs bg-bg ${className}`}
    >
      {icon && <Icon name={icon} size={12} />}
      {children}
    </span>
  );
}
