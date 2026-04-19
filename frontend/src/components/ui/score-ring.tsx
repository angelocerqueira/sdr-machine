interface ScoreRingProps {
  value: number;
  size?: 32 | 56 | 72;
  className?: string;
}

function scoreColor(value: number): string {
  if (value >= 80) return "var(--score-high)";
  if (value >= 50) return "var(--score-mid)";
  return "var(--score-low)";
}

export function ScoreRing({ value, size = 56, className = "" }: ScoreRingProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const strokeWidth = size <= 32 ? 2.5 : 3;
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = scoreColor(clamped);

  const fontSize = size <= 32 ? 11 : size <= 56 ? 15 : 20;
  const subSize = size <= 32 ? 0 : size <= 56 ? 9 : 11;

  return (
    <div className={`relative inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono tabular-nums font-[480] leading-none"
          style={{ fontSize, color }}
        >
          {clamped}
        </span>
        {subSize > 0 && (
          <span className="font-mono text-text-subtle leading-none mt-0.5" style={{ fontSize: subSize }}>
            / 100
          </span>
        )}
      </div>
    </div>
  );
}
