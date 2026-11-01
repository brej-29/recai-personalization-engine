export type Catalog = {
  n: number
  id: string[]; t: string[]; a: string[]; f: number[]; m: number[]; y: number[]; s: number[]; p: number[]
  g: number[][]; k: number[][]; c: string[]; col: string[]; u: string[]
  media: string[]; genres: string[]; tags: string[]
}
export type Weights = { a: number; b: number; c: number }
export type Data = {
  cat: Catalog
  d: number
  emb: Float32Array // n*d, unit rows (centering and adapter already applied offline)
  xy: Float32Array // n*2 in 0..1
  search: string[]
  w: Weights
  tagPtr: Uint32Array // CSR tag/genre TF-IDF channel, rows L2-normalised
  tagIdx: Uint16Array
  tagVal: Float32Array
  tagDim: number
  popz: Float32Array // log-popularity z-score within family
}

export const MEDIA_LABEL = ['Anime', 'Anime films', 'Manga', 'Manhwa', 'Manhua', 'Novels', 'Movies', 'Series']
export const MEDIA_CODE = ['ANM', 'FLM', 'MGA', 'MHW', 'MHU', 'NVL', 'MOV', 'SER']
const BASE = import.meta.env.BASE_URL + 'data/'

type Parts = {
  cat: Catalog; meta: { d: number; weights: Weights; tag_vocab: number }
  emb: ArrayBuffer; xy: ArrayBuffer; ptr: ArrayBuffer; idx: ArrayBuffer; val: ArrayBuffer; popz: ArrayBuffer
}

export async function loadData(): Promise<Data> {
  const bin = (f: string) => fetch(BASE + f).then((r) => r.arrayBuffer())
  const [cat, meta, emb, xy, ptr, idx, val, popz] = await Promise.all([
    fetch(BASE + 'catalog.json').then((r) => r.json() as Promise<Catalog>),
    fetch(BASE + 'meta.json').then((r) => r.json() as Promise<Parts['meta']>),
    bin('emb.bin'), bin('atlas.bin'), bin('tags_indptr.bin'), bin('tags_indices.bin'), bin('tags_data.bin'), bin('popz.bin'),
  ])
  return parseData({ cat, meta, emb, xy, ptr, idx, val, popz })
}

export function parseData(p: Parts): Data {
  const { cat, meta } = p
  const q = new Int8Array(p.emb)
  const emb = new Float32Array(q.length)
  for (let i = 0; i < q.length; i++) emb[i] = q[i] / 127
  const u16 = new Uint16Array(p.xy)
  const xy = new Float32Array(u16.length)
  for (let i = 0; i < u16.length; i++) xy[i] = u16[i] / 65535
  const half = (b: ArrayBuffer) => {
    const h = new Uint16Array(b)
    const out = new Float32Array(h.length)
    for (let i = 0; i < h.length; i++) out[i] = f16(h[i])
    return out
  }
  const search = cat.t.map((t, i) => norm(t + ' ' + cat.a[i]))
  return {
    cat, d: meta.d, emb, xy, search, w: meta.weights, tagDim: meta.tag_vocab,
    tagPtr: new Uint32Array(p.ptr), tagIdx: new Uint16Array(p.idx), tagVal: half(p.val), popz: half(p.popz),
  }
}

/** IEEE half to float. */
function f16(h: number): number {
  const s = h & 0x8000 ? -1 : 1
  const e = (h >> 10) & 0x1f
  const f = h & 0x3ff
  if (e === 0) return s * 2 ** -14 * (f / 1024)
  if (e === 31) return f ? NaN : s * Infinity
  return s * 2 ** (e - 15) * (1 + f / 1024)
}

export function norm(s: string): string {
  return s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim()
}

export function coverUrl(cat: Catalog, i: number): string | null {
  const c = cat.c[i]
  return c ? 'https://s4.anilist.co/file/anilistcdn/media/' + c : null
}

export function sourceUrl(cat: Catalog, i: number): string {
  const id = cat.id[i]
  return id.startsWith('al:')
    ? `https://anilist.co/${cat.m[i] <= 1 ? 'anime' : 'manga'}/${id.slice(3)}`
    : `https://www.imdb.com/title/${id.slice(3)}/`
}
