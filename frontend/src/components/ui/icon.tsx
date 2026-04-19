/**
 * SDR Machine Design System — Custom stroke-based icons
 * viewBox 20x20, stroke-width 1.25, no icon library dependency
 */

export type IconName =
  | "search" | "plus" | "check" | "x"
  | "arrow-r" | "arrow-d" | "chevron-d" | "chevron-r"
  | "filter" | "sort" | "more"
  | "home" | "board" | "list" | "lead" | "job"
  | "globe" | "phone" | "mail" | "pin" | "doc"
  | "sparkle" | "sun" | "moon"
  | "sidebar-open" | "sidebar-close"
  | "info" | "warn" | "error" | "ok" | "bolt"
  | "wa" | "building" | "link" | "cnpj" | "score"
  | "settings" | "copy" | "external" | "drag" | "folder" | "empty"
  | "refresh" | "message";

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

export function Icon({ name, size = 16, className = "", style }: IconProps) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.25,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    style,
    "aria-hidden": true as const,
  };

  switch (name) {
    case "search":
      return <svg {...common}><circle cx="9" cy="9" r="5.5"/><path d="M13 13l3.5 3.5"/></svg>;
    case "plus":
      return <svg {...common}><path d="M10 4v12M4 10h12"/></svg>;
    case "check":
      return <svg {...common}><path d="M4 10.5L8 14.5L16 6"/></svg>;
    case "x":
      return <svg {...common}><path d="M5 5l10 10M15 5L5 15"/></svg>;
    case "arrow-r":
      return <svg {...common}><path d="M4 10h12M11 5l5 5-5 5"/></svg>;
    case "arrow-d":
      return <svg {...common}><path d="M10 4v12M5 11l5 5 5-5"/></svg>;
    case "chevron-d":
      return <svg {...common}><path d="M5 8l5 5 5-5"/></svg>;
    case "chevron-r":
      return <svg {...common}><path d="M8 5l5 5-5 5"/></svg>;
    case "filter":
      return <svg {...common}><path d="M3 5h14M6 10h8M8 15h4"/></svg>;
    case "sort":
      return <svg {...common}><path d="M6 4v12M6 16l-2-2M6 16l2-2M14 16V4M14 4l-2 2M14 4l2 2"/></svg>;
    case "more":
      return <svg {...common}><circle cx="4.5" cy="10" r="1"/><circle cx="10" cy="10" r="1"/><circle cx="15.5" cy="10" r="1"/></svg>;
    case "home":
      return <svg {...common}><path d="M3 9l7-5 7 5v7a1 1 0 0 1-1 1h-3v-5H8v5H5a1 1 0 0 1-1-1V9z"/></svg>;
    case "board":
      return <svg {...common}><rect x="3" y="4" width="4" height="12" rx="1"/><rect x="9" y="4" width="4" height="8" rx="1"/><rect x="15" y="4" width="2" height="10" rx="1"/></svg>;
    case "list":
      return <svg {...common}><path d="M4 5h12M4 10h12M4 15h12"/></svg>;
    case "lead":
      return <svg {...common}><circle cx="10" cy="7" r="3"/><path d="M3.5 17c1-3.5 3.5-5 6.5-5s5.5 1.5 6.5 5"/></svg>;
    case "job":
      return <svg {...common}><rect x="3" y="6" width="14" height="10" rx="1"/><path d="M7 6V4h6v2"/></svg>;
    case "globe":
      return <svg {...common}><circle cx="10" cy="10" r="6"/><path d="M4 10h12M10 4c2 2 2 10 0 12M10 4c-2 2-2 10 0 12"/></svg>;
    case "phone":
      return <svg {...common}><path d="M5 4h3l1.5 3.5-2 1c.5 2 2 3.5 4 4l1-2L16 12v3c0 1-1 2-2 2-5 0-10-5-10-10 0-1 1-3 1-3z"/></svg>;
    case "mail":
      return <svg {...common}><rect x="3" y="5" width="14" height="10" rx="1"/><path d="M3 6l7 5 7-5"/></svg>;
    case "pin":
      return <svg {...common}><path d="M10 17s-5-4.5-5-9a5 5 0 0 1 10 0c0 4.5-5 9-5 9z"/><circle cx="10" cy="8" r="1.5"/></svg>;
    case "doc":
      return <svg {...common}><path d="M5 3h7l3 3v11H5z"/><path d="M12 3v3h3"/></svg>;
    case "sparkle":
      return <svg {...common}><path d="M10 3v4M10 13v4M3 10h4M13 10h4M6 6l2 2M14 14l-2-2M6 14l2-2M14 6l-2 2"/></svg>;
    case "sun":
      return <svg {...common}><circle cx="10" cy="10" r="3.5"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.5 4.5l1.5 1.5M14 14l1.5 1.5M4.5 15.5L6 14M14 6l1.5-1.5"/></svg>;
    case "moon":
      return <svg {...common}><path d="M15 11a6 6 0 0 1-7.5-7.5A6.5 6.5 0 1 0 15 11z"/></svg>;
    case "sidebar-open":
      return <svg {...common}><rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M12 4v12"/><path d="M7 8l2 2-2 2"/></svg>;
    case "sidebar-close":
      return <svg {...common}><rect x="3" y="4" width="14" height="12" rx="1.5"/><path d="M12 4v12"/><path d="M9 8l-2 2 2 2"/></svg>;
    case "info":
      return <svg {...common}><circle cx="10" cy="10" r="7"/><path d="M10 9v4M10 7v.01"/></svg>;
    case "warn":
      return <svg {...common}><path d="M10 3l7 13H3L10 3z"/><path d="M10 8v4M10 14v.01"/></svg>;
    case "error":
      return <svg {...common}><circle cx="10" cy="10" r="7"/><path d="M7 7l6 6M13 7l-6 6"/></svg>;
    case "ok":
      return <svg {...common}><circle cx="10" cy="10" r="7"/><path d="M7 10l2 2 4-4"/></svg>;
    case "bolt":
      return <svg {...common}><path d="M11 2L4 11h5l-1 7 7-9h-5l1-7z"/></svg>;
    case "wa":
      return <svg {...common}><path d="M3.5 16.5l1-3A7 7 0 1 1 6.5 16l-3 .5z"/><path d="M7.5 8c.3 1 .7 1.8 1.4 2.5S10.5 12 11.5 12.5l1-1.3 2 1-1 1.8c-2.5 0-5.5-2-6.5-5l1.5-1L8 8z"/></svg>;
    case "building":
      return <svg {...common}><rect x="4" y="3" width="12" height="14" rx="1"/><path d="M8 7h1M11 7h1M8 10h1M11 10h1M8 13h1M11 13h1"/></svg>;
    case "link":
      return <svg {...common}><path d="M9 6h-2a4 4 0 0 0 0 8h2M11 6h2a4 4 0 0 1 0 8h-2M7 10h6"/></svg>;
    case "cnpj":
      return <svg {...common}><rect x="3" y="5" width="14" height="10" rx="1"/><path d="M3 8h14M7 11h2M11 11h3M7 13h6"/></svg>;
    case "score":
      return <svg {...common}><path d="M3 17l3-3M7 14l3-5M10 10l3 2M13 12l4-6"/></svg>;
    case "settings":
      return <svg {...common}><circle cx="10" cy="10" r="2.5"/><path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.5 1.5M13.5 13.5L15 15M5 15l1.5-1.5M13.5 6.5L15 5"/></svg>;
    case "copy":
      return <svg {...common}><rect x="6" y="6" width="10" height="10" rx="1"/><path d="M4 12V5a1 1 0 0 1 1-1h7"/></svg>;
    case "external":
      return <svg {...common}><path d="M11 4h5v5M16 4l-7 7M14 11v4a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h4"/></svg>;
    case "drag":
      return <svg {...common}><circle cx="7" cy="6" r="0.8"/><circle cx="13" cy="6" r="0.8"/><circle cx="7" cy="10" r="0.8"/><circle cx="13" cy="10" r="0.8"/><circle cx="7" cy="14" r="0.8"/><circle cx="13" cy="14" r="0.8"/></svg>;
    case "folder":
      return <svg {...common}><path d="M3 6a1 1 0 0 1 1-1h3l2 2h7a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6z"/></svg>;
    case "empty":
      return <svg {...common}><rect x="3" y="6" width="14" height="10" rx="1"/><path d="M3 10h14M7 13h6"/></svg>;
    case "refresh":
      return <svg {...common}><path d="M16 4v4h-4M4 16v-4h4"/><path d="M5.5 8A5.5 5.5 0 0 1 16 8M14.5 12a5.5 5.5 0 0 1-10.5 0"/></svg>;
    case "message":
      return <svg {...common}><path d="M4 4h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H8l-4 3V5a1 1 0 0 1 1-1z"/></svg>;
    default:
      return <svg {...common}><rect x="4" y="4" width="12" height="12" rx="1"/></svg>;
  }
}
