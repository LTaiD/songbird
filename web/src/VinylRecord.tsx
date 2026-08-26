import { useRef } from 'react'
import { motion, useAnimationFrame, useMotionValue, useReducedMotion } from 'motion/react'
import { Bird } from '@phosphor-icons/react'

type Spin = 'idle' | 'active'

const BASE_VEL = 20

function norm(a: number) {
  while (a > 180) a -= 360
  while (a < -180) a += 360
  return a
}

function Grooves() {
  const grooves = [46, 42, 38, 34, 30, 26]
  return (
    <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
      <circle cx="50" cy="50" r="49" className="fill-ink" />
      <circle cx="50" cy="50" r="49" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.6" />
      {grooves.map((r) => (
        <circle key={r} cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="0.5" />
      ))}
      <circle cx="50" cy="50" r="18" className="fill-paper-2" />
      <circle cx="50" cy="50" r="18" fill="none" stroke="rgba(0,0,0,0.08)" strokeWidth="0.5" />
    </svg>
  )
}

const GRADIENT =
  'linear-gradient(125deg, rgba(255,255,255,0.5) 0%, rgba(255,255,255,0.14) 26%, rgba(255,255,255,0) 52%, rgba(255,255,255,0) 78%, rgba(255,255,255,0.08) 100%)'
// A softer, tighter highlight on the exact opposite end of the record.
const GRADIENT_OPP =
  'linear-gradient(305deg, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0.08) 18%, rgba(255,255,255,0) 40%)'
// Fixed light: the grooves spin under it, but the specular gloss stays put.
const GLOSS = `${GRADIENT_OPP}, ${GRADIENT}`

export function VinylRecord({ size = 240, state = 'idle', spin = true }: { size?: number; state?: Spin; spin?: boolean }) {
  const reduce = useReducedMotion()
  const ref = useRef<HTMLDivElement>(null)
  const angle = useMotionValue(0)
  const vel = useRef(BASE_VEL)
  const dragging = useRef(false)
  const lastAngle = useRef(0)
  const lastTime = useRef(0)
  const idleInteractive = spin && state === 'idle'

  useAnimationFrame((_, delta) => {
    if (reduce || !idleInteractive || dragging.current) return
    vel.current += (BASE_VEL - vel.current) * Math.min(1, delta / 600)
    angle.set(angle.get() + (vel.current * delta) / 1000)
  })

  function pointerAngle(e: React.PointerEvent) {
    const r = ref.current!.getBoundingClientRect()
    return (Math.atan2(e.clientY - (r.top + r.height / 2), e.clientX - (r.left + r.width / 2)) * 180) / Math.PI
  }
  function onDown(e: React.PointerEvent) {
    if (!idleInteractive) return
    dragging.current = true
    lastAngle.current = pointerAngle(e)
    lastTime.current = performance.now()
    ref.current?.setPointerCapture(e.pointerId)
  }
  function onMove(e: React.PointerEvent) {
    if (!dragging.current) return
    const pa = pointerAngle(e)
    const d = norm(pa - lastAngle.current)
    angle.set(angle.get() + d)
    const now = performance.now()
    const dt = now - lastTime.current
    if (dt > 0) vel.current = (d / dt) * 1000
    lastAngle.current = pa
    lastTime.current = now
  }
  function onUp() {
    dragging.current = false
  }

  const bird = <Bird weight="fill" className="text-ink" style={{ width: size * 0.16, height: size * 0.16 }} />
  const spindle = (
    <div
      className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-paper"
      style={{ width: size * 0.03, height: size * 0.03 }}
    />
  )

  if (spin && state === 'active') {
    return (
      <div className="relative rounded-full drop-shadow-[0_24px_48px_rgba(0,0,0,0.34)]" style={{ width: size, height: size }}>
        <motion.div
          className="absolute inset-0"
          animate={reduce ? undefined : { rotate: 360 }}
          transition={reduce ? undefined : { duration: 2.4, repeat: Infinity, ease: 'linear' }}
        >
          <Grooves />
          <div className="absolute inset-0 grid place-items-center">{bird}</div>
        </motion.div>
        <div className="pointer-events-none absolute inset-0 rounded-full" style={{ background: GLOSS }} />
        {spindle}
      </div>
    )
  }

  return (
    <motion.div
      ref={ref}
      onPointerDown={onDown}
      onPointerMove={onMove}
      onPointerUp={onUp}
      onPointerCancel={onUp}
      className={`relative touch-none rounded-full drop-shadow-[0_24px_48px_rgba(0,0,0,0.34)] ${idleInteractive ? 'cursor-grab active:cursor-grabbing' : ''}`}
      style={{ width: size, height: size }}
    >
      <motion.div
        className="absolute inset-0"
        animate={reduce || !spin ? undefined : { rotate: 360 }}
        transition={reduce || !spin ? undefined : { duration: 14, repeat: Infinity, ease: 'linear' }}
      >
        <Grooves />
      </motion.div>
      <motion.div className="pointer-events-none absolute inset-0 grid place-items-center" style={{ rotate: idleInteractive ? angle : 0 }}>{bird}</motion.div>
      {spindle}
      <div className="pointer-events-none absolute inset-0 rounded-full" style={{ background: GLOSS }} />
    </motion.div>
  )
}

export function DiskMark({ size = 96, className = '' }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} className={className} aria-hidden>
      <circle cx="50" cy="50" r="49" className="fill-ink" />
      <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="0.6" />
      <circle cx="50" cy="50" r="33" fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="0.6" />
      <circle cx="50" cy="50" r="18" className="fill-paper-2" />
      <circle cx="50" cy="50" r="2" className="fill-ink" />
    </svg>
  )
}
