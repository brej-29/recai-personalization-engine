import type { Data } from './data'
import { norm } from './data'

export type Hit = { i: number; score: number; why: string[] }

/** Typeahead: prefix > word-start > substring, ties broken by popularity. */
export function searchTitles(data: Data, query: string, limit = 7): number[] {
  const q = norm(query)
  if (q.length < 2) return []
  const out: [number, number][] = []
  const { search, cat } = data
  for (let i = 0; i < search.length; i++) {
    const s = search[i]
    const at = s.indexOf(q)
    if (at < 0) continue
    const rank = at === 0 ? 0 : s[at - 1] === ' ' ? 1 : 2
    out.push([rank * 1e9 - Math.log1p(cat.p[i]) * 1e6 + at, i])
  }
  return out.sort((a, b) => a[0] - b[0]).slice(0, limit).map((x) => x[1])
}

function seedVector(data: Data, seeds: number[]): Float32Array {
  const { emb, d } = data
  const q = new Float32Array(d)
  for (const s of seeds) for (let j = 0; j < d; j++) q[j] += emb[s * d + j]
  let nrm = 0
  for (let j = 0; j < d; j++) nrm += q[j] * q[j]
  nrm = Math.sqrt(nrm) || 1
  for (let j = 0; j < d; j++) q[j] /= nrm
  return q
}

export type Options = { media: number | null; hideFranchise: boolean; k: number; perMediumCap?: number }

export function recommend(data: Data, seeds: number[], opt: Options): Hit[] {
  if (!seeds.length) return []
  const { emb, d, cat, w, tagPtr, tagIdx, tagVal, tagDim, popz } = data
  const q = seedVector(data, seeds)
  // mean of the seeds' tag rows (not renormalised, as in kindred.engine)
  const tq = new Float32Array(tagDim)
  for (const s of seeds) for (let p = tagPtr[s]; p < tagPtr[s + 1]; p++) tq[tagIdx[p]] += tagVal[p] / seeds.length
  const fr = new Set(seeds.map((s) => cat.f[s]))
  const seedSet = new Set(seeds)
  const scored: { fused: number; i: number; dot: number }[] = []
  for (let i = 0; i < cat.n; i++) {
    if (seedSet.has(i)) continue
    if (opt.media !== null && cat.m[i] !== opt.media) continue
    if (opt.hideFranchise && fr.has(cat.f[i])) continue
    let dot = 0
    const o = i * d
    for (let j = 0; j < d; j++) dot += emb[o + j] * q[j]
    let tg = 0
    for (let p = tagPtr[i]; p < tagPtr[i + 1]; p++) tg += tq[tagIdx[p]] * tagVal[p]
    scored.push({ fused: w.a * dot + w.b * tg + w.c * popz[i], i, dot })
  }
  scored.sort((x, y) => y.fused - x.fused || x.i - y.i)
  const picked: typeof scored = []
  const cap = opt.media === null ? (opt.perMediumCap ?? Math.ceil(opt.k / 4)) : opt.k
  const used = new Array(8).fill(0)
  const seenF = new Set<number>()
  const take = (r: (typeof scored)[number]) => {
    seenF.add(cat.f[r.i]) // one title per franchise: an adaptation is not a second discovery
    used[cat.m[r.i]]++
    picked.push(r)
  }
  if (opt.media === null) {
    // pass 1: the best title of every shelf, so every medium gets a say
    const have = new Set<number>()
    for (const r of scored) {
      if (have.has(cat.m[r.i]) || seenF.has(cat.f[r.i])) continue
      have.add(cat.m[r.i])
      take(r)
      if (have.size === 8) break
    }
  }
  const chosen = new Set(picked.map((r) => r.i))
  for (const r of scored) {
    if (picked.length >= opt.k) break
    if (chosen.has(r.i) || used[cat.m[r.i]] >= cap || seenF.has(cat.f[r.i])) continue
    take(r)
  }
  picked.sort((x, y) => y.fused - x.fused || x.i - y.i)
  return picked.map(({ i, dot }) => ({ i, score: dot, why: explain(data, seeds, i) }))
}

/** Shared genres and themes between the result and any seed. */
export function explain(data: Data, seeds: number[], i: number): string[] {
  const { cat } = data
  const names: string[] = []
  const seedG = new Set<number>()
  const seedK = new Set<number>()
  for (const s of seeds) {
    cat.g[s].forEach((x) => seedG.add(x))
    cat.k[s].forEach((x) => seedK.add(x))
  }
  for (const t of cat.k[i]) if (seedK.has(t)) names.push(cat.tags[t])
  for (const g of cat.g[i]) if (seedG.has(g)) names.push(cat.genres[g])
  return names.slice(0, 3)
}

/** Cosine similarity as a two-digit readout (cos x 100). Not a probability. */
export function readout(hits: Hit[]): number[] {
  return hits.map((h) => Math.max(0, Math.min(99, Math.round(h.score * 100))))
}
