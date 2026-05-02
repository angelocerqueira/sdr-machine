export function cleanPhone(phone: string | null | undefined): string {
  if (!phone) return "";
  return phone.replace(/\D/g, "");
}

export function buildWaLink(phone: string | null | undefined, message?: string): string | null {
  const cleaned = cleanPhone(phone);
  if (!cleaned) return null;
  const withCountry = cleaned.startsWith("55") ? cleaned : `55${cleaned}`;
  const base = `https://wa.me/${withCountry}`;
  return message ? `${base}?text=${encodeURIComponent(message)}` : base;
}

export function formatRelativeDate(input: string | Date | null | undefined): string {
  if (!input) return "";
  const date = typeof input === "string" ? new Date(input) : input;
  if (Number.isNaN(date.getTime())) return "";

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHour = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "agora";
  if (diffMin < 60) return `há ${diffMin}min`;
  if (diffHour < 24) return `há ${diffHour}h`;
  if (diffDay === 1) return "ontem";
  if (diffDay < 7) return `há ${diffDay}d`;

  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}
