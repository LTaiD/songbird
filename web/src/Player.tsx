import { useRef, useState } from 'react'
import { Pause, Play } from '@phosphor-icons/react'

function fmt(t: number) {
  if (!isFinite(t)) return '0:00'
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

export function Player({ src, kind }: { src: string; kind: 'audio' | 'video' }) {
  const ref = useRef<HTMLVideoElement | HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [cur, setCur] = useState(0)
  const [dur, setDur] = useState(0)
  const [scrubbing, setScrubbing] = useState(false)

  function toggle() {
    const el = ref.current
    if (!el) return
    if (el.paused) el.play()
    else el.pause()
  }
  function seek(v: number) {
    if (ref.current) ref.current.currentTime = v
    setCur(v)
  }

  const mediaEvents = {
    onTimeUpdate: (e: React.SyntheticEvent<HTMLMediaElement>) => setCur(e.currentTarget.currentTime),
    onLoadedMetadata: (e: React.SyntheticEvent<HTMLMediaElement>) => setDur(e.currentTarget.duration),
    onPlay: () => setPlaying(true),
    onPause: () => setPlaying(false),
    onEnded: () => setPlaying(false),
  }

  const PlayPause = (
    <button
      type="button"
      onClick={toggle}
      aria-label={playing ? 'Pause' : 'Play'}
      className="grid size-10 shrink-0 cursor-pointer place-items-center rounded-full bg-ink text-paper transition-transform active:scale-95"
    >
      {playing ? <Pause weight="fill" size={18} /> : <Play weight="fill" size={18} />}
    </button>
  )

  const pct = dur > 0 ? (cur / dur) * 100 : 0
  const scrubber = (
    <>
      <input
        type="range"
        min={0}
        max={dur || 0}
        step="0.1"
        value={cur}
        onChange={(e) => seek(Number(e.target.value))}
        onPointerDown={() => setScrubbing(true)}
        onPointerUp={() => setScrubbing(false)}
        onPointerCancel={() => setScrubbing(false)}
        aria-label="Seek"
        style={{ background: `linear-gradient(to right, currentColor ${pct}%, var(--line) ${pct}%)` }}
        className={`w-full cursor-pointer appearance-none rounded-full text-ink transition-[height] duration-150 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-current [&::-moz-range-thumb]:transition-all [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-current [&::-webkit-slider-thumb]:shadow-[0_1px_3px_rgba(0,0,0,0.3)] [&::-webkit-slider-thumb]:transition-all ${scrubbing ? 'h-2 [&::-moz-range-thumb]:size-4 [&::-webkit-slider-thumb]:size-4' : 'h-1 [&::-moz-range-thumb]:size-3 [&::-webkit-slider-thumb]:size-3'}`}
      />
      <span className="shrink-0 text-xs tabular-nums text-muted">
        {fmt(cur)} / {fmt(dur)}
      </span>
    </>
  )

  if (kind === 'video') {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-line bg-black shadow-panel">
        <video
          ref={ref as React.RefObject<HTMLVideoElement>}
          src={src}
          playsInline
          onClick={toggle}
          {...mediaEvents}
          className="h-full w-full cursor-pointer object-contain"
        />
        <div className="absolute inset-x-0 bottom-0 flex items-center gap-3 bg-gradient-to-t from-black/75 to-transparent p-3 [&_.accent-ink]:accent-paper [&_button]:bg-paper [&_button]:text-ink [&_input]:text-paper [&_input]:accent-paper [&_span]:text-paper">
          {PlayPause}
          {scrubber}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-paper-2 p-4 shadow-panel">
      <audio ref={ref as React.RefObject<HTMLAudioElement>} src={src} {...mediaEvents} />
      {PlayPause}
      {scrubber}
    </div>
  )
}
