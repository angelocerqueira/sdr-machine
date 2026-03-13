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
        className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm text-white transition-colors"
      >
        📱 Abrir WhatsApp
      </a>
      {onMarkSent && (
        <button
          onClick={onMarkSent}
          className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-sm transition-colors"
        >
          ✓ Marcar como enviado
        </button>
      )}
    </div>
  );
}
