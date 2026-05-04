"use client";

import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="py-16 px-6" style={{ background: "var(--paper-0)", borderTop: "1px solid var(--line-2)" }}>
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-10 md:grid-cols-[2fr_3fr]">
          <div>
            <Link href="/" className="font-semibold tracking-tight" style={{ color: "var(--ink-0)", fontSize: "15px" }}>
              SDR Machine
            </Link>
            <p style={{ color: "var(--ink-3)", fontSize: "14px", marginTop: "8px" }}>Instrumento de prospecção.</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-8">
            <FooterColumn title="Produto" links={[
              { label: "Como funciona", href: "#como-funciona" },
              { label: "Veja em prática", href: "#pratica" },
              { label: "Agendar demo", href: "#agendar" },
            ]} />
            <FooterColumn title="Empresa" links={[
              { label: "Sollertis", href: "https://sollertis.com.br", external: true },
              { label: "Contato", href: "mailto:contato@sollertis.com.br" },
            ]} />
            <FooterColumn title="Legal" links={[
              { label: "Privacidade", href: "/privacidade" },
              { label: "Termos", href: "/termos" },
            ]} />
          </div>
        </div>

        <div className="flex items-center justify-between mt-12 pt-6" style={{ borderTop: "1px solid var(--line-2)" }}>
          <div className="font-mono" style={{ color: "var(--ink-3)", fontSize: "11px" }}>© 2026 Sollertis</div>
          <a
            href="https://www.linkedin.com/company/sollertis"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--ink-3)" }}
          >
            LinkedIn
          </a>
        </div>
      </div>
    </footer>
  );
}

type FooterLink = { label: string; href: string; external?: boolean };

function FooterColumn({ title, links }: { title: string; links: FooterLink[] }) {
  return (
    <div>
      <div
        className="font-mono mb-3"
        style={{ color: "var(--ink-3)", fontSize: "10px", letterSpacing: "0.18em", textTransform: "uppercase" }}
      >
        {title}
      </div>
      <ul className="space-y-2">
        {links.map((l) => (
          <li key={l.label}>
            <a
              href={l.href}
              target={l.external ? "_blank" : undefined}
              rel={l.external ? "noreferrer" : undefined}
              style={{ color: "var(--ink-2)", fontSize: "14px" }}
            >
              {l.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
