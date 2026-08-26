export function StackedDisks({ className = '' }: { className?: string }) {
  const records = 7
  const rx = 205
  const ry = 60
  const spacing = 112
  const startY = 80
  const amp = 30
  const grooves = 16

  return (
    <svg viewBox="0 0 480 960" className={className} aria-hidden preserveAspectRatio="xMidYMid meet">
      {Array.from({ length: records }).map((_, i) => {
        const cx = 250 + amp * Math.sin(i * 0.9)
        const cy = startY + i * spacing
        const rot = (i - (records - 1) / 2) * 5
        const t = `rotate(${rot} ${cx} ${cy})`
        return (
          <g key={i} transform={t}>
            <ellipse cx={cx} cy={cy} rx={rx} ry={ry} className="fill-ink" />
            {Array.from({ length: grooves }).map((__, j) => {
              const f = 0.94 - j * 0.045
              return (
                <ellipse
                  key={j}
                  cx={cx}
                  cy={cy}
                  rx={rx * f}
                  ry={ry * f}
                  fill="none"
                  stroke="rgba(255,255,255,0.55)"
                  strokeWidth={0.9}
                />
              )
            })}
            <ellipse cx={cx} cy={cy} rx={rx * 0.2} ry={ry * 0.2} className="fill-paper-2" />
          </g>
        )
      })}
    </svg>
  )
}
