import type { Transition, Variants } from 'motion/react'

export const springs = {
  fast: { type: 'spring', stiffness: 420, damping: 32 } satisfies Transition,
  moderate: { type: 'spring', stiffness: 220, damping: 26 } satisfies Transition,
  slow: { type: 'spring', stiffness: 120, damping: 22 } satisfies Transition,
}

export const ease = [0.16, 1, 0.3, 1] as const

export function reveal(reduce: boolean, i = 0): Variants {
  return {
    hidden: reduce ? { opacity: 1 } : { opacity: 0, y: 24 },
    show: {
      opacity: 1,
      y: 0,
      transition: reduce ? { duration: 0 } : { duration: 0.6, ease, delay: i * 0.06 },
    },
  }
}

export const staggerParent: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
}
