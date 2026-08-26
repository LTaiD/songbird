import { useEffect, useState } from 'react'
import { parseEmbed } from './lib/embed'
import { Player } from './Player'

export function MediaPreview({ url, file }: { url: string; file: File | null }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setObjectUrl(null)
      return
    }
    const u = URL.createObjectURL(file)
    setObjectUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [file])

  if (file && objectUrl) {
    const isVideo = file.type.startsWith('video/') || /\.(mp4|webm|mov|m4v)$/i.test(file.name)
    return <Player src={objectUrl} kind={isVideo ? 'video' : 'audio'} />
  }

  const embed = parseEmbed(url)
  if (!embed) return null

  if (embed.kind === 'iframe') {
    return (
      <div className={`w-full overflow-hidden rounded-2xl border border-line bg-surface shadow-panel ${embed.vertical ? 'mx-auto aspect-[9/16] max-w-[280px]' : 'aspect-video'}`}>
        <iframe
          src={embed.src}
          title={`${embed.source} preview`}
          loading="lazy"
          allow="autoplay; encrypted-media; picture-in-picture; clipboard-write"
          allowFullScreen
          className="h-full w-full rounded-[14px] border-0 bg-black"
        />
      </div>
    )
  }
  return <Player src={embed.src} kind={embed.kind === 'video' ? 'video' : 'audio'} />
}
