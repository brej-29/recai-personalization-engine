import { describe, expect, it } from 'vitest'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { type Data, parseData } from './data'
import { explain, readout, recommend, searchTitles } from './engine'

// 5 titles, 2-d unit vectors. 0 and 1 share a franchise; 4 is far away.
function toy(): Data {
  const v = [[1, 0], [0.98, 0.2], [0.8, 0.6], [0.6, 0.8], [0, 1]]
  return {
    d: 2,
    emb: Float32Array.from(v.flat()),
    xy: new Float32Array(10),
    search: ['frieren', 'frieren movie', 'solo leveling', 'parasite', 'zzz'],
    w: { a: 1, b: 0, c: 0 }, tagPtr: new Uint32Array(6), tagIdx: new Uint16Array(0), tagVal: new Float32Array(0), tagDim: 1,
    popz: new Float32Array(5),
    cat: {
      n: 5, id: ['a', 'b', 'c', 'd', 'e'], t: ['Frieren', 'Frieren Movie', 'Solo Leveling', 'Parasite', 'Zzz'],
      a: ['', '', '', '', ''], f: [1, 1, 2, 3, 4], m: [0, 2, 3, 6, 7], y: [0, 0, 0, 0, 0], s: [0, 0, 0, 0, 0],
      p: [100, 5, 50, 10, 1], g: [[0], [0], [0, 1], [1], [2]], k: [[0], [0], [0], [1], []], c: [], col: [], u: [],
      media: [], genres: ['Fantasy', 'Drama', 'Horror'], tags: ['Elf', 'Body Horror'],
    },
  }
}

describe('engine', () => {
  it('ranks by cosine and hides the seed franchise', () => {
    const hits = recommend(toy(), [0], { media: null, hideFranchise: true, k: 5, perMediumCap: 5 })
    expect(hits.map((h) => h.i)).toEqual([2, 3, 4])
  })
  it('keeps the franchise when asked, but one title per franchise', () => {
    const hits = recommend(toy(), [2], { media: null, hideFranchise: false, k: 5, perMediumCap: 5 })
    expect(hits.map((h) => h.i)).toEqual([3, 1, 4])
  })
  it('filters by medium', () => {
    const hits = recommend(toy(), [0], { media: 6, hideFranchise: true, k: 5 })
    expect(hits.map((h) => h.i)).toEqual([3])
  })
  it('averages several seeds', () => {
    const hits = recommend(toy(), [2, 4], { media: null, hideFranchise: true, k: 2, perMediumCap: 5 })
    expect(hits[0].i).toBe(3)
  })
  it('explains with shared themes before genres', () => {
    expect(explain(toy(), [0], 2)).toEqual(['Elf', 'Fantasy'])
  })
  it('searches by prefix before substring and ignores short queries', () => {
    const d = toy()
    expect(searchTitles(d, 'f')).toEqual([])
    expect(searchTitles(d, 'fri')[0]).toBe(0)
  })
  it('reads cosine as two digits', () => {
    expect(readout([{ i: 0, score: 0.614, why: [] }, { i: 1, score: 1.2, why: [] }])).toEqual([61, 99])
  })
})

describe('parity with the Python reference on the shipped files', () => {
  const dir = resolve(__dirname, '../public/data')
  const fx = resolve(__dirname, 'fixtures/parity.json')
  it.skipIf(!existsSync(fx) || !existsSync(dir + '/emb.bin'))('top-10 matches kindred.export_web.reference_recommend', () => {
    const buf = (f: string) => { const b = readFileSync(resolve(dir, f)); return b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength) as ArrayBuffer }
    const data = parseData({
      cat: JSON.parse(readFileSync(resolve(dir, 'catalog.json'), 'utf8')), meta: JSON.parse(readFileSync(resolve(dir, 'meta.json'), 'utf8')),
      emb: buf('emb.bin'), xy: buf('atlas.bin'), ptr: buf('tags_indptr.bin'), idx: buf('tags_indices.bin'), val: buf('tags_data.bin'), popz: buf('popz.bin'),
    })
    const cases = JSON.parse(readFileSync(fx, 'utf8')) as { seeds: number[]; media: number | null; expected: number[] }[]
    for (const c of cases) {
      const got = recommend(data, c.seeds, { media: c.media, hideFranchise: true, k: 12 }).map((h) => h.i)
      const overlap = got.filter((x) => c.expected.includes(x)).length
      expect(overlap).toBeGreaterThanOrEqual(11) // float32 vs float64 accumulation may swap a tied pair
    }
  })
})
