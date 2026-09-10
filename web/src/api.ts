export type IdentifyResult = {
  song: string
  artist: string
  apple: string
  spotify: string
  tiktok: string
}

export type IdentifyInput = { url: string } | { file: File }

export type ReleaseKind = 'Album' | 'EP' | 'Single'
export type SongMeta = { preview: string | null; album: string | null; kind: ReleaseKind | null }

const KIND_RANK: Record<ReleaseKind, number> = { Album: 3, EP: 2, Single: 1 }

// ponytail: iTunes tags the collectionName with " - Single"/" - EP"; anything else reads as an album.
// Album takes precedence, so pick the highest-ranked release across all matches for the track.
export async function songMeta(song: string, artist: string): Promise<SongMeta> {
  const term = encodeURIComponent(`${song} ${artist}`.trim())
  try {
    const res = await fetch(`https://itunes.apple.com/search?term=${term}&entity=song&limit=8`)
    const results = (await res.json())?.results ?? []
    if (!results.length) return { preview: null, album: null, kind: null }
    const releases = results.map((r: { collectionName?: string }) => {
      const name = r.collectionName ?? ''
      const kind: ReleaseKind = / - EP$/.test(name) ? 'EP' : / - Single$/.test(name) ? 'Single' : 'Album'
      return { name: name.replace(/ - (EP|Single)$/, ''), kind }
    })
    releases.sort((a: { kind: ReleaseKind }, b: { kind: ReleaseKind }) => KIND_RANK[b.kind] - KIND_RANK[a.kind])
    const best = releases[0]
    return { preview: results[0]?.previewUrl ?? null, album: best.name || null, kind: best.kind }
  } catch {
    return { preview: null, album: null, kind: null }
  }
}

// First image from a Wikipedia search — keyless and CORS-friendly.
// ponytail: occasionally a logo/wrong page; swap for a licensed image API if accuracy matters.
export async function artistImage(artist: string): Promise<string | null> {
  const q = encodeURIComponent(`${artist} musician`)
  try {
    const url = `https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch=${q}&gsrlimit=1&prop=pageimages&piprop=thumbnail&pithumbsize=600&format=json&origin=*`
    const pages = (await (await fetch(url)).json())?.query?.pages ?? {}
    const first = Object.values(pages)[0] as { thumbnail?: { source?: string } } | undefined
    return first?.thumbnail?.source ?? null
  } catch {
    return null
  }
}

export async function identify(input: IdentifyInput): Promise<IdentifyResult> {
  const body = new FormData()
  if ('url' in input) body.append('url', input.url)
  else body.append('file', input.file)

  let res: Response
  try {
    res = await fetch(`${import.meta.env.VITE_API_BASE ?? ''}/identify`, { method: 'POST', body })
  } catch {
    throw new Error('Could not reach the identifier. Is the backend running?')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok || !data || 'error' in data) {
    throw new Error((data && data.error) || 'Identification failed.')
  }
  return data as IdentifyResult
}
