import { useEffect, useMemo, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { toast } from 'sonner'
import {
  Bird,
  FileAudio,
  LinkSimple,
  MagnifyingGlass,
  Play,
  UploadSimple,
} from '@phosphor-icons/react'
import { identify, songMeta, artistImage, type IdentifyResult, type SongMeta } from './api'
import { MediaPreview } from './MediaPreview'
import { Player } from './Player'
import { parseEmbed } from './lib/embed'
import { reveal, springs, staggerParent } from './motion'
import { VinylRecord, DiskMark } from './VinylRecord'
import { Backdrop } from './Backdrop'
import { AppleMusicIcon, SoundcloudIcon, SpotifyIcon, TiktokIcon, YoutubeIcon } from './BrandIcons'

export default function App() {
  return (
    <div className="min-h-[100dvh] text-ink">
      <Nav />
      <Hero />
      <HowItWorks />
      <WorksWith />
      <Footer />
    </div>
  )
}

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-paper/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6 sm:px-8">
        <a href="#top" className="flex items-center gap-2 font-display text-xl tracking-tight">
          <Bird weight="fill" size={24} />
          Songbird
        </a>
        <div className="flex items-center gap-3 sm:gap-5">
          <a href="#top" className="cursor-pointer rounded-full bg-ink px-4 py-1.5 text-sm font-medium text-paper">
            Try It
          </a>
          <a href="#how" className="hidden cursor-pointer text-sm text-muted sm:block">How It Works</a>
          <a href="#works" className="hidden cursor-pointer text-sm text-muted sm:block">Works With</a>
        </div>
      </nav>
    </header>
  )
}

function Hero() {
  const reduce = useReducedMotion()
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [status, setStatus] = useState<'idle' | 'submitting'>('idle')
  const [result, setResult] = useState<IdentifyResult | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  const busy = status === 'submitting'
  const hasInput = url.trim().length > 0 || file !== null
  const canSubmit = !busy && hasInput
  const previewable = useMemo(() => (file ? true : parseEmbed(url) !== null), [file, url])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!canSubmit) return
    setStatus('submitting')
    setResult(null)
    try {
      const input = url.trim() ? { url: url.trim() } : { file: file as File }
      setResult(await identify(input))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Identification failed.')
    } finally {
      setStatus('idle')
    }
  }

  function pickFile(f: File | null) {
    setFile(f)
    if (f) setUrl('')
    setResult(null)
  }

  return (
    <section id="top" className="relative overflow-hidden">
      <Backdrop />
      <div className="mx-auto grid max-w-7xl gap-14 px-6 pt-16 pb-24 sm:px-8 lg:min-h-[calc(100dvh-4rem)] lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch lg:gap-16 lg:pb-16">
        <motion.div variants={staggerParent} initial="hidden" animate="show" className="max-w-xl">
          <motion.h1 variants={reveal(!!reduce, 0)} className="font-display text-[2.6rem] leading-[0.95] tracking-tight text-balance sm:text-6xl lg:text-7xl">
            Know the song from any live recording.
          </motion.h1>
          <motion.p variants={reveal(!!reduce, 1)} className="mt-6 max-w-md text-lg leading-relaxed text-muted text-pretty">
            Most song finders need the studio track playing through a speaker. Songbird is made for live music. Give it a live band, a cover, or a jam where people play the song their own way. It traces the performance back to the studio original and hands you the track.
          </motion.p>
          <motion.div variants={reveal(!!reduce, 2)} className="mt-9">
            <IdentifyTool
              url={url}
              file={file}
              busy={busy}
              canSubmit={canSubmit}
              dragging={dragging}
              fileInput={fileInput}
              onUrl={(v) => { setUrl(v); if (v) pickFile(null) }}
              onFile={pickFile}
              onDragging={setDragging}
              onSubmit={onSubmit}
            />
          </motion.div>
        </motion.div>

        <div className="flex justify-center lg:h-full lg:items-center lg:justify-end">
          <Stage busy={busy} result={result} previewable={previewable} url={url} file={file} reduce={!!reduce} />
        </div>
      </div>
    </section>
  )
}

function IdentifyTool(props: {
  url: string
  file: File | null
  busy: boolean
  canSubmit: boolean
  dragging: boolean
  fileInput: React.RefObject<HTMLInputElement | null>
  onUrl: (v: string) => void
  onFile: (f: File | null) => void
  onDragging: (d: boolean) => void
  onSubmit: (e: React.FormEvent) => void
}) {
  const { url, file, busy, canSubmit, dragging, fileInput, onUrl, onFile, onDragging, onSubmit } = props
  return (
    <form onSubmit={onSubmit} className="rounded-2xl border border-line bg-surface p-3 shadow-panel">
      <div className="flex items-center gap-2 rounded-xl border border-line bg-paper px-3 focus-within:shadow-[0_0_0_3px_var(--ring)]">
        <LinkSimple className="shrink-0 text-muted" size={18} />
        <input
          type="url"
          inputMode="url"
          value={url}
          onChange={(e) => onUrl(e.target.value)}
          placeholder="Paste a video link"
          aria-label="Media URL"
          disabled={busy}
          className="w-full bg-transparent py-3 text-base text-ink outline-none placeholder:text-muted disabled:opacity-60"
        />
      </div>

      <div className="my-2 flex items-center gap-3 px-1 text-xs text-muted">
        <span className="h-px flex-1 bg-line" />
        or
        <span className="h-px flex-1 bg-line" />
      </div>

      <button
        type="button"
        onClick={() => fileInput.current?.click()}
        onDragOver={(e) => { e.preventDefault(); onDragging(true) }}
        onDragLeave={() => onDragging(false)}
        onDrop={(e) => { e.preventDefault(); onDragging(false); onFile(e.dataTransfer.files?.[0] ?? null) }}
        disabled={busy}
        className={`flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed px-4 py-4 text-sm transition-[background-color,border-color] disabled:opacity-60 ${
          dragging ? 'border-ink bg-ink/5 text-ink' : 'border-line text-muted'
        }`}
      >
        <UploadSimple size={18} />
        {file ? <span className="truncate text-ink">{file.name}</span> : <span>Drag an audio or video file, or click to choose</span>}
      </button>
      <input ref={fileInput} type="file" accept="audio/*,video/*" className="sr-only" onChange={(e) => onFile(e.target.files?.[0] ?? null)} />

      <MagneticSubmit disabled={!canSubmit} busy={busy} />
    </form>
  )
}

function MagneticSubmit({ disabled, busy }: { disabled: boolean; busy: boolean }) {
  const reduce = useReducedMotion()
  return (
    <motion.button
      type="submit"
      disabled={disabled}
      whileTap={reduce || disabled ? undefined : { scale: 0.98 }}
      className="mt-2 flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-ink px-4 py-3.5 text-base font-semibold text-paper transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
    >
      <MagnifyingGlass weight="bold" size={18} />
      {busy ? <Identifying reduce={!!reduce} /> : 'Identify song'}
    </motion.button>
  )
}

function Identifying({ reduce }: { reduce: boolean }) {
  if (reduce) return <span>Identifying…</span>
  return (
    <span className="inline-flex items-baseline">
      <motion.span
        className="bg-clip-text text-transparent"
        style={{
          backgroundImage:
            'linear-gradient(90deg, rgba(255,255,255,0.55) 0%, rgba(255,255,255,0.55) 35%, #fff 50%, rgba(255,255,255,0.55) 65%, rgba(255,255,255,0.55) 100%)',
          backgroundSize: '200% 100%',
        }}
        animate={{ backgroundPosition: ['150% 0%', '-50% 0%'] }}
        transition={{ duration: 2.6, repeat: Infinity, repeatDelay: 0.15, ease: 'easeInOut' }}
      >
        Identifying
      </motion.span>
      <span>…</span>
    </span>
  )
}

function Stage({ busy, result, previewable, url, file, reduce }: {
  busy: boolean
  result: IdentifyResult | null
  previewable: boolean
  url: string
  file: File | null
  reduce: boolean
}) {
  let content: React.ReactNode
  if (busy) {
    content = (
      <div className="grid place-items-center py-10">
        <VinylRecord size={240} state="active" />
      </div>
    )
  } else if (result) {
    content = <ResultCard result={result} reduce={reduce} />
  } else if (previewable) {
    content = (
      <>
        <MediaPreview url={url} file={file} />
        <p className="mt-3 text-center text-sm text-muted">Ready! Hit identify to find the original song.</p>
      </>
    )
  } else {
    content = (
      <div className="flex flex-col items-center gap-6 py-8">
        <VinylRecord size={240} state="idle" />
        <p className="text-sm text-muted">Your music will be here.</p>
      </div>
    )
  }
  // Player fits snugly to the video; loading and result stretch to fill the column.
  const isPlayer = !busy && !result && previewable
  return <Panel full={!isPlayer} reduce={reduce}>{content}</Panel>
}

function Panel({ children, full, reduce }: { children: React.ReactNode; full: boolean; reduce: boolean }) {
  return (
    <motion.div
      layout={!reduce}
      transition={springs.moderate}
      className={`flex w-full flex-col justify-center rounded-2xl border border-line bg-surface p-5 shadow-panel ${full ? 'lg:h-full' : ''}`}
    >
      {children}
    </motion.div>
  )
}

const RELEASE_LABEL: Record<NonNullable<SongMeta['kind']>, string> = {
  Album: 'From the album',
  EP: 'From the EP',
  Single: 'Released as a single',
}

function ResultCard({ result, reduce }: { result: IdentifyResult; reduce: boolean }) {
  const [meta, setMeta] = useState<SongMeta | null>(null)
  const [img, setImg] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    songMeta(result.song, result.artist).then((m) => live && setMeta(m))
    artistImage(result.artist).then((u) => live && setImg(u))
    return () => { live = false }
  }, [result.song, result.artist])

  return (
      <motion.div
        initial={reduce ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.moderate}
      >
        <motion.div variants={staggerParent} initial="hidden" animate="show">
          <motion.p variants={reveal(reduce, 0)} className="text-xs font-medium uppercase tracking-[0.16em] text-muted">
            Studio original
          </motion.p>
          <motion.h2 variants={reveal(reduce, 1)} className="mt-2 font-display text-3xl leading-tight tracking-tight text-balance">
            {result.song}
          </motion.h2>
          <motion.p variants={reveal(reduce, 2)} className="mt-1 text-lg text-muted">{result.artist}</motion.p>
          {meta?.kind && (
            <motion.p initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="mt-2 text-sm text-muted">
              {RELEASE_LABEL[meta.kind]}
              {meta.album && meta.kind !== 'Single' ? <span className="text-ink"> {meta.album}</span> : null}
            </motion.p>
          )}
          {meta?.preview && (
            <motion.div variants={reveal(reduce, 3)} className="mt-5">
              <p className="mb-2 text-xs text-muted">Preview</p>
              <Player src={meta.preview} kind="audio" />
            </motion.div>
          )}
          <motion.div variants={reveal(reduce, 4)} className="mt-6 grid grid-cols-3 gap-2">
            <LinkButton href={result.apple} label="Apple Music" icon={<AppleMusicIcon size={20} />} />
            <LinkButton href={result.spotify} label="Spotify" icon={<SpotifyIcon size={20} />} />
            <LinkButton href={result.tiktok} label="TikTok" icon={<TiktokIcon size={20} />} />
          </motion.div>
          {img && (
            <motion.figure
              initial={reduce ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springs.moderate}
              className="mt-6 overflow-hidden rounded-xl border border-line"
            >
              <img src={img} alt={result.artist} loading="lazy" className="h-44 w-full object-cover" />
              <figcaption className="bg-paper px-4 py-2.5 text-xs text-muted">{result.artist}</figcaption>
            </motion.figure>
          )}
        </motion.div>
      </motion.div>
  )
}

function LinkButton({ href, label, icon }: { href: string; label: string; icon: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={`Open ${label}`}
      className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border border-line bg-paper px-2 py-4 text-center text-sm font-medium text-ink transition-transform active:scale-[0.98]"
    >
      {icon}
      <span>{label}</span>
    </a>
  )
}

function HowItWorks() {
  const reduce = useReducedMotion()
  const steps = [
    { title: 'Paste a video link or drop a file', body: 'Give Songbird a recording of the performance you want traced back to its source.', visual: <VinylRecord size={128} state="idle" spin={false} /> },
    { title: 'It listens and matches', body: 'Songbird embeds the audio in overlapping windows with MuQ, matches a local catalog, then reranks by chord progression.', visual: <MiniPlayer /> },
    { title: 'Get the studio original', body: 'The performance is traced back to the record it came from, so you can go straight to the original song.', visual: <MiniResult /> },
  ]
  return (
    <section id="how" className="border-t border-line bg-paper-2/60">
      <div className="mx-auto max-w-7xl px-6 py-24 sm:px-8">
        <div className="max-w-2xl">
          <h2 className="font-display text-4xl leading-[0.95] tracking-tight text-balance sm:text-5xl">How It Works</h2>
          <p className="mt-4 text-lg leading-relaxed text-muted text-pretty">From a rough clip to the record it came from, in one step.</p>
          <p className="mt-4 leading-relaxed text-muted text-pretty">
            Songbird cuts the recording into short, overlapping windows and turns each into a vector that describes the music. A vector similarity search finds the closest studio songs. A chord-progression rerank then picks the best match. Songbird reads the music itself, so it works on a live show, a cover, or a jam, even when the key, tempo, or instruments change.
          </p>
        </div>

        <motion.ol
          variants={staggerParent}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.2 }}
          className="mt-14 grid gap-5 md:grid-cols-3"
        >
          {steps.map((s, i) => (
            <motion.li key={s.title} variants={reveal(!!reduce, i)} className="flex flex-col rounded-2xl border border-line bg-surface p-6 shadow-panel">
              <div className="grid h-44 place-items-center rounded-xl bg-paper-2">{s.visual}</div>
              <span className="mt-6 font-display text-2xl tabular-nums">{String(i + 1).padStart(2, '0')}</span>
              <h3 className="mt-2 text-xl font-semibold tracking-tight">{s.title}</h3>
              <p className="mt-2 leading-relaxed text-muted">{s.body}</p>
            </motion.li>
          ))}
        </motion.ol>
      </div>
    </section>
  )
}

function MiniPlayer() {
  return (
    <div className="flex w-full max-w-[230px] items-center gap-3 rounded-xl border border-line bg-paper p-4 shadow-panel">
      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-ink text-paper">
        <Play weight="fill" size={15} />
      </span>
      <div className="flex-1">
        <div className="h-1.5 w-full rounded-full bg-line">
          <div className="h-1.5 w-2/5 rounded-full bg-ink" />
        </div>
        <div className="mt-2 flex justify-between text-[10px] tabular-nums text-muted">
          <span>0:48</span>
          <span>2:11</span>
        </div>
      </div>
    </div>
  )
}

function MiniResult() {
  return (
    <div className="w-full max-w-[230px] rounded-xl border border-line bg-paper p-4 shadow-panel">
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted">Studio original</p>
      <div className="mt-3 flex items-center gap-3">
        <DiskMark size={44} />
        <div className="flex-1">
          <div className="h-3 w-28 rounded-full bg-ink" />
          <div className="mt-2 h-2.5 w-20 rounded-full bg-line" />
        </div>
      </div>
    </div>
  )
}

function WorksWith() {
  const reduce = useReducedMotion()
  const items = [
    { label: 'YouTube', icon: <YoutubeIcon size={28} /> },
    { label: 'TikTok', icon: <TiktokIcon size={28} /> },
    { label: 'SoundCloud', icon: <SoundcloudIcon size={28} /> },
    { label: 'Any file', icon: <FileAudio weight="fill" size={28} /> },
  ]
  return (
    <section id="works" className="border-t border-line">
      <div className="mx-auto max-w-7xl px-6 py-24 sm:px-8">
        <div className="grid gap-12 md:grid-cols-[1fr_1.4fr] md:items-center">
          <h2 className="font-display text-3xl leading-[0.95] tracking-tight text-balance sm:text-4xl">
            Bring the recording from anywhere.
          </h2>
          <motion.ul
            variants={staggerParent}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, amount: 0.4 }}
            className="grid grid-cols-2 gap-4 sm:grid-cols-4"
          >
            {items.map((it, i) => (
              <motion.li key={it.label} variants={reveal(!!reduce, i)} className="flex flex-col items-center gap-3 rounded-2xl border border-line bg-surface px-4 py-8 text-ink">
                {it.icon}
                <span className="text-sm font-medium">{it.label}</span>
              </motion.li>
            ))}
          </motion.ul>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-line bg-paper-2/60">
      <div className="mx-auto max-w-7xl px-6 py-24 sm:px-8">
        <div className="flex flex-col gap-12 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-3 font-display text-4xl tracking-tight sm:text-5xl">
              <Bird weight="fill" size={40} />
              Songbird
            </div>
            <p className="mt-6 max-w-md leading-relaxed text-muted">
              A research build. Song embeddings use MuQ, licensed CC BY-NC 4.0. It runs on the CPU, so identification takes a moment.
            </p>
          </div>
          <div className="flex gap-8 text-sm text-muted">
            <a href="#top" className="cursor-pointer">Try It</a>
            <a href="#how" className="cursor-pointer">How It Works</a>
            <a href="#works" className="cursor-pointer">Works With</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
