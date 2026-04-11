import { MarketingNavbar } from "@/components/marketing/marketing-navbar";

export const metadata = {
  title: "SDR Machine — Prospecção Automatizada com IA",
  description:
    "Encontre negócios, analise sua presença digital, gere landing pages e envie mensagens no WhatsApp — tudo automatizado.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <MarketingNavbar />
      {children}
    </>
  );
}
