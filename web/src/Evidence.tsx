import { useEffect, useRef, useState } from 'react'
import { Seg } from './Seg'

export type Silo = {
  rec_edges_same_format: number
  rec_edges_cross_format_within_manga_type: number
  rec_edges_anime_to_print_or_back: number
  anime_with_print_source_in_sample: number
  titles: number
}

export function useInView<T extends Element>(): [React.RefObject<T | null>, boolean] {
  const ref = useRef<T>(null)
  const [seen, setSeen] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) { setSeen(true); return }
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setSeen(true); io.disconnect() } }, { threshold: 0.35 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return [ref, seen]
}

/** Scoreboard-style settle: digits fire left to right, no sliding. Idle means "show the real value". */
function useSettle(target: string, go: boolean): string {
  const [frames, setFrames] = useState<string | null>(null)
  useEffect(() => {
    setFrames(null)
    if (!go || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let frame = 0
    const id = setInterval(() => {
      frame++
      const settled = Math.floor(frame / 3)
      if (settled >= target.length) { clearInterval(id); setFrames(null); return }
      setFrames([...target].map((c, i) => (!/\d/.test(c) || i < settled ? c : String((frame * 7 + i * 3) % 10))).join(''))
    }, 45)
    return () => clearInterval(id)
  }, [target, go])
  return frames ?? target
}

const fmt = (n: number) => n.toLocaleString('en-US')

export function Silo({ silo }: { silo: Silo | null }) {
  const [ref, seen] = useInView<HTMLDivElement>()
  const same = silo ? fmt(silo.rec_edges_same_format) : '0'
  const cross = silo ? String(silo.rec_edges_anime_to_print_or_back) : '0'
  const a = useSettle(same, seen)
  const b = useSettle(cross, seen)
  return (
    <section id="silo" aria-labelledby="silo-h">
      <h2 id="silo-h">Taste is filed by format, so it never crosses the aisle.</h2>
      <p className="lead">
        AniList lets users recommend a title to fans of another, and over {silo ? fmt(silo.rec_edges_same_format) : 'tens of thousands of'} of
        those links exist in the {silo ? fmt(silo.titles) : ''} most popular non-adult titles. None of them goes from an anime to a
        manga or novel. Collaborative filtering needs people who rated both sides, and for these catalogues there are none to learn from.
      </p>
      <div className="cols" ref={ref}>
        <div className="ledger silo-well">
          <div>
            <Seg text={a} pad={6} className="big glow" label={`${same} recommendations inside one format`} />
            <p className="cap">user recommendations between two anime, or two manga, manhwa, manhua or novels</p>
          </div>
          <div>
            <Seg text={b} pad={6} className="big zero glow" label={`${cross} recommendations from anime to manga or back`} />
            <p className="cap">user recommendations from an anime to a manga or novel, or back</p>
          </div>
        </div>
        <div>
          <p>
            The only signal that does link the two sides is adaptation: {silo ? fmt(silo.anime_with_print_source_in_sample) : 'over a thousand'} of
            these anime say which manga or novel they came from. That is the bridge the benchmark below walks over:
            people who liked this anime also liked <em>that</em> anime, which comes from <em>this</em> manga.
          </p>
          <p style={{ marginTop: 16 }}>
            So Kindred has to read what titles are about. The question is how well taste learned inside one medium survives the jump to another.
          </p>
        </div>
      </div>
    </section>
  )
}

/** The bridge the benchmark walks: A and B are recommended together, B comes from T. */
export function Test() {
  return (
    <section id="test" aria-labelledby="test-h">
      <h2 id="test-h">The test: find the manga that the anime your fans also liked came from.</h2>
      <p className="lead">
        For an anime A, fans on AniList recommend another anime B. B was adapted from a manga or novel T. Kindred sees only the text
        of A (plot, genres, themes, never the title) and must rank T among thousands of print titles. The same walk runs from print to anime.
        Titles in the same franchise as A are removed first.
      </p>
      <figure className="diagram">
        <svg viewBox="0 0 880 250" role="img" aria-labelledby="dg-t dg-d">
          <title id="dg-t">Benchmark construction</title>
          <desc id="dg-d">Anime A is linked to anime B by user recommendations. B is linked to manga T by adaptation. Kindred must go from A directly to T.</desc>
          <g className="node" transform="translate(30 60)"><rect width="190" height="104" rx="2" style={{ stroke: 'var(--m0)' }} /><text x="95" y="46" textAnchor="middle">Anime A</text><text x="95" y="72" textAnchor="middle" className="s">the seed, text only</text></g>
          <g className="node" transform="translate(345 60)"><rect width="190" height="104" rx="2" style={{ stroke: 'var(--m0)' }} /><text x="95" y="46" textAnchor="middle">Anime B</text><text x="95" y="72" textAnchor="middle" className="s">fans of A recommend it</text></g>
          <g className="node" transform="translate(660 60)"><rect width="190" height="104" rx="2" style={{ stroke: 'var(--m2)' }} /><text x="95" y="46" textAnchor="middle">Manga or novel T</text><text x="95" y="72" textAnchor="middle" className="s">B is adapted from it</text></g>
          <path className="edge" d="M220 112 H345" /><path className="edge" d="M535 112 H660" />
          <text x="282" y="98" textAnchor="middle" className="s">users recommend</text>
          <text x="598" y="98" textAnchor="middle" className="s">adaptation</text>
          <path className="edge hot" d="M125 164 C 125 236, 755 236, 755 164" />
          <path className="arrow" d="M749 172 L755 162 L761 172" />
          <text x="440" y="226" textAnchor="middle" className="s hotl">Kindred has to draw this line, from text alone</text>
        </svg>
      </figure>
    </section>
  )
}
