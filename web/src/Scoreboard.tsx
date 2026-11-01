import { type Silo, useInView } from './Evidence'
import { Seg } from './Seg'

export type Evidence = {
  xm: {
    model: string; queries: number; pairs: number; adapter_dim: number; truth_pop: number
    weights: { a: number; b: number; c: number }
    systems: { key: string; label: string; v: number; lo: number; hi: number; hit: number; pop: number }[]
    hyp: { id: string; claim: string; supported: boolean; diff?: number; lo?: number; hi?: number; rel?: number; filtered?: number; unfiltered?: number; ratio?: number }[]
    secondary: { queries: number; systems: { key: string; label: string; v: number; lo: number; hi: number }[] }
    direction: Record<string, Record<string, number>>
  }
  ml: null | {
    counts: { eligible_users: number; evaluated_users: number; catalogue_movies_with_movielens_link: number }
    k: Record<string, Record<string, { v: number; lo: number; hi: number }>>
    crossover: number | null
    h6: { model: string; diff: number; lo: number; hi: number; gain: string[]; loss: string[] }
  }
  silo: Silo
  payload: { bytes: Record<string, number>; n: number; d: number }
}

type Hyp = Evidence['xm']['hyp'][number]

const f3 = (x: number) => x.toFixed(3)
const sgn = (x: number) => (x >= 0 ? '+' : '-') + Math.abs(x).toFixed(3)
const pct = (x: number) => `${Math.round(x * 100)}%`
const tone = (k: string) =>
  k === 'fusion' ? 'var(--lit)' : k.startsWith('fusion') || k.startsWith('adapter') ? 'var(--m4)'
  : k === 'zero_shot' || k === 'centering' ? 'var(--m5)' : 'var(--faint)'

function hypLine(h: Hyp, g: (k: string) => number): string {
  if (h.id === 'H1') return `Embedding ${f3(g('zero_shot'))} against tags ${f3(g('tag_tfidf'))}: difference ${sgn(h.diff!)} (95% CI ${sgn(h.lo!)} to ${sgn(h.hi!)}). Curated tags beat raw embeddings.`
  if (h.id === 'H2') return `Centring changes the score by ${sgn(h.diff!)} (CI ${sgn(h.lo!)} to ${sgn(h.hi!)}), ${(h.rel! * 100).toFixed(1)}% relative. No evidence that closing the embedding gap helps here.`
  if (h.id === 'H3') return `Adapter ${f3(g('adapter'))} against ${f3(g('zero_shot'))}: ${sgn(h.diff!)} (CI ${sgn(h.lo!)} to ${sgn(h.hi!)}), ${(h.rel! * 100).toFixed(0)}% relative. Taste learned inside one medium transfers to another.`
  if (h.id === 'H4') return `Kindred ${f3(g('fusion'))} against the best non-learned baseline ${f3(g('tag_tfidf'))}: ${sgn(h.diff!)} (CI ${sgn(h.lo!)} to ${sgn(h.hi!)}), ${(h.rel! * 100).toFixed(0)}% relative.`
  return `With the franchise filter ${f3(h.filtered!)}, without ${f3(h.unfiltered!)}: ratio ${h.ratio!.toFixed(2)}. Franchise leakage adds about ${Math.round((h.ratio! - 1) * 100)}%, not the 50% the threshold asked for.`
}

export function Scoreboard({ ev }: { ev: Evidence | null }) {
  const [ref, seen] = useInView<HTMLDivElement>()
  if (!ev) {
    return (
      <section id="scoreboard" aria-labelledby="sb-h">
        <h2 id="sb-h">Scoreboard</h2>
        <p className="lead">Loading the benchmark results.</p>
      </section>
    )
  }
  const { xm } = ev
  const g = (k: string) => xm.systems.find((s) => s.key === k)!
  const cap = Math.ceil(Math.max(...xm.systems.map((s) => s.hi), 0.25) * 20) / 20
  return (
    <section id="scoreboard" aria-labelledby="sb-h">
      <h2 id="sb-h">Text alone is not enough. Text plus tags, shaped by taste, is.</h2>
      <p className="lead">
        Test split: {xm.queries.toLocaleString()} queries, {xm.pairs.toLocaleString()} relevant pairs, scored once. The metric is NDCG@10, where 1.0 would put every
        relevant title at the top. Bars show the mean; the bracket is a 95% bootstrap interval over queries.
      </p>
      <div className="board-table" ref={ref} role="table" aria-label="NDCG at 10 by system">
        {xm.systems.map((s) => (
          <div className={`srow ${s.key === 'fusion' ? 'top' : ''}`} role="row" key={s.key}>
            <span className="name" role="rowheader">{s.label}</span>
            <span className="meter" aria-hidden="true"
              style={{ ['--tick' as string]: (0.05 / cap) * 100, ['--p' as string]: seen ? (s.v / cap) * 100 : 0, ['--c' as string]: tone(s.key), ['--lo' as string]: (s.lo / cap) * 100, ['--hi' as string]: (s.hi / cap) * 100 }}>
              <i className="ci" />
            </span>
            <span className="val" role="cell">
              <Seg text={f3(s.v)} className={s.key === 'fusion' ? 'glow' : ''} label={`NDCG at 10 ${f3(s.v)}`} />
            </span>
            <span className="ci-txt" role="cell">{f3(s.lo)} to {f3(s.hi)}</span>
          </div>
        ))}
      </div>
      <p className="note">
        Popularity bias: {pct(g('fusion').pop)} of Kindred's top ten come from the most popular decile of titles, against {pct(xm.truth_pop)} in the labels.
        Without the popularity term the score is {f3(g('fusion-no-pop').v)} and the share is {pct(g('fusion-no-pop').pop)}.
        The app ships the full formula: {xm.weights.a} x embedding + {xm.weights.b} x tags + {xm.weights.c} x popularity.
      </p>

      <h3 className="h3">Pre-registered hypotheses</h3>
      <p className="lead small">Written down before scoring, with thresholds. {xm.hyp.filter((h) => !h.supported).length} of {xm.hyp.length} failed.</p>
      <ul className="hyps">
        {xm.hyp.map((h) => (
          <li key={h.id}>
            <span className={`verdict ${h.supported ? 'yes' : 'no'}`}><i />{h.supported ? 'Supported' : 'Not supported'}</span>
            <div>
              <p><Seg text={h.id} className="hid" label={h.id} /><span>{h.claim}</span></p>
              <p className="why">{hypLine(h, (k) => g(k).v)}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
