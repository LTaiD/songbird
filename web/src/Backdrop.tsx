const W = 1200
const H = 820

function rng(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function buildField() {
  const r = rng(11)
  const discs: { x: number; y: number; rx: number; ry: number; rot: number; g: number }[] = []
  let guard = 0
  while (discs.length < 15 && guard < 600) {
    guard++
    const rx = 30 + r() * 140
    const x = r() * W
    const y = r() * H
    const clash = discs.some((d) => Math.hypot(d.x - x, d.y - y) < (d.rx + rx) * 0.72)
    if (clash) continue
    discs.push({
      x,
      y,
      rx,
      ry: rx * (0.16 + r() * 0.74),
      rot: (r() - 0.5) * 120,
      g: Math.min(11, Math.max(3, Math.round(rx / 14))),
    })
  }
  return discs
}

const FIELD = buildField()
// ponytail: RNG put discs 2 & 9 touching side-by-side on the right; hand-place them as a spaced vertical stack.
FIELD[2] = { ...FIELD[2], x: 1150, y: 110 }
FIELD[9] = { ...FIELD[9], x: 1150, y: 470 }

export function Backdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 h-full w-full opacity-[0.13]"
      >
        {FIELD.map((d, i) => (
          <g key={i} transform={`translate(${d.x} ${d.y}) rotate(${d.rot})`}>
            <ellipse rx={d.rx} ry={d.ry} className="fill-ink" />
            {Array.from({ length: d.g }).map((_, j) => {
              const f = 1 - (j + 1) / (d.g + 2)
              return (
                <ellipse key={j} rx={d.rx * f} ry={d.ry * f} fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth={0.8} />
              )
            })}
            <ellipse rx={d.rx * 0.14} ry={d.ry * 0.14} className="fill-paper-2" />
          </g>
        ))}
      </svg>
    </div>
  )
}
