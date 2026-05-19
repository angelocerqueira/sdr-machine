interface Props {
  count: number;
  onClick: () => void;
}

export function ScrollToBottomFab({ count, onClick }: Props) {
  if (count <= 0) return null;
  const label = count === 1 ? "1 mensagem nova" : `${count} mensagens novas`;
  return (
    <button
      type="button"
      onClick={onClick}
      className="inbox-scroll-fab"
      aria-label={label}
    >
      <span className="inbox-scroll-fab-arrow">↓</span>
      <span>{label}</span>
    </button>
  );
}
