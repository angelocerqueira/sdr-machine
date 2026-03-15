"use client";

interface WhatsAppButtonProps {
  whatsappLink: string;
  onMarkSent?: () => void;
}

export function WhatsAppButton({ whatsappLink, onMarkSent }: WhatsAppButtonProps) {
  return (
    <div className="flex gap-3">
      <a
        href={whatsappLink}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2.5 px-5 py-2.5 bg-[#25D366] hover:bg-[#20BD5A] rounded-lg text-[13px] font-medium text-white transition-default shadow-lg shadow-[#25D366]/20"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
          <path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.612.616l4.573-1.449A11.944 11.944 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.37 0-4.567-.702-6.414-1.905l-.244-.157-3.176 1.005 1.04-3.1-.17-.254A9.953 9.953 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/>
        </svg>
        Abrir WhatsApp
      </a>
      {onMarkSent && (
        <button
          onClick={onMarkSent}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-surface-raised hover:bg-surface-overlay border border-border hover:border-accent/30 rounded-lg text-[13px] font-medium text-text-secondary hover:text-accent transition-default"
        >
          <svg className="w-3.5 h-3.5" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M2 7l3.5 3.5L12 3" />
          </svg>
          Marcar como enviado
        </button>
      )}
    </div>
  );
}
