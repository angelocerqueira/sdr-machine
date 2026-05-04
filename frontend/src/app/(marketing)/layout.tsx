import { MarketingNavbar } from "@/components/marketing/marketing-navbar";

export const metadata = {
  title: "SDR Machine — Instrumento de prospecção B2B",
  description:
    "Acha o lead, lê o site, prepara a abordagem e abre a conversa. Pare de pagar SDR pra abrir LinkedIn.",
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="theme-marketing-dark min-h-screen">
      <MarketingNavbar />
      {children}
    </div>
  );
}
