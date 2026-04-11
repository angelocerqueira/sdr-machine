import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t border-border-subtle py-10 px-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-gradient-to-br from-accent to-accent-dim flex items-center justify-center">
            <span className="text-bg text-[8px] font-bold">S</span>
          </div>
          <span className="text-sm text-text-muted">SDR Machine</span>
        </div>

        <div className="flex items-center gap-6 text-xs text-text-muted">
          <a href="#como-funciona" className="hover:text-text transition-colors">Como Funciona</a>
          <a href="#features" className="hover:text-text transition-colors">Features</a>
          <a href="#agendar" className="hover:text-text transition-colors">Agendar Demo</a>
        </div>

        <p className="text-xs text-text-muted">
          Sollertis Solutions · {new Date().getFullYear()}
        </p>
      </div>
    </footer>
  );
}
