import type { Evidence } from './Scoreboard'

const f2 = (x: number) => x.toFixed(2)

function mlLabel(s: string): string {
  if (s === 'Dense:gte-small') return 'Embedding only (gte-small)'
  if (s === 'Kindred') return 'Kindred scoring, centred, no adapter'
  if (s.startsWith('Kindred+adapter:')) return 'Kindred scoring with adapter (' + s.split(':')[1] + ')'
  return s
}

export function Sanity({ ev }: { ev: Evidence | null }) {
  const ml = ev?.ml
  if (!ml) return null
  const ks = Object.keys(ml.k)
  const systems = Object.keys(ml.k[ks[0]])
  return (
    <section id="movies" aria-labelledby="mv-h">
      <h2 id="mv-h">Where ratings exist, use ratings.</h2>
      <p className="lead">
        Sanity check on MovieLens 25M, movies only: {ml.counts.evaluated_users.toLocaleString()} users, {ml.counts.catalogue_movies_with_movielens_link.toLocaleString()} catalogue
        movies, k liked movies as the seed, NDCG@10 on the rest. Collaborative filtering wins from the first seed and by a wide margin, so Kindred
        should not be used for movie to movie picks on a site that already has ratings.
      </p>
      <div className="tablewrap" tabIndex={0} role="region" aria-label="MovieLens results table">
      <table className="mltable">
        <caption className="sr">NDCG at 10 on MovieLens by number of seed movies</caption>
        <thead>
          <tr><th scope="col">System</th>{ks.map((k) => <th scope="col" key={k}>k = {k}</th>)}</tr>
        </thead>
        <tbody>
          {systems.map((s) => (
            <tr key={s}>
              <th scope="row" style={{ textTransform: 'none', letterSpacing: 0, font: 'inherit', color: 'inherit' }}>{mlLabel(s)}</th>
              {ks.map((k) => <td key={k}>{f2(ml.k[k][s].v)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      <p className="note">
        H6 (does the anime and manga adapter help movie to movie?): mixed. For {ml.h6.model} the Recall@10 change is {ml.h6.diff >= 0 ? '+' : '-'}{Math.abs(ml.h6.diff).toFixed(4)}
        (95% CI {ml.h6.lo.toFixed(4)} to {ml.h6.hi.toFixed(4)}), real but tiny; it helps {ml.h6.gain.join(' and ') || 'none'} and hurts {ml.h6.loss.join(' and ') || 'none'}.
        Per-medium centring alone does better here than the adapter, which is why live action is the weakest part of the product.
      </p>
    </section>
  )
}

const limits = (ev: Evidence | null): [string, string][] => {
  const sec = ev?.xm.secondary
  const g = (k: string) => sec?.systems.find((x) => x.key === k)?.v.toFixed(3) ?? 'n/a'
  return [
  ['Labels are a proxy.', `No human ever said "this anime fan will like that manga". The benchmark walks recommendation edges between anime and then follows the adaptation link, so it rewards titles that have an anime or print counterpart. On the ${sec?.queries ?? 'n/a'} genuine manga, manhwa and manhua cross-format queries the full system scores ${g('fusion')} against ${g('tag_tfidf')} for tags alone, which points the same way but is a small sample.`],
  ['One seed, not five.', 'The benchmark queries with a single title. The app lets you add up to five and averages them; that behaviour is tested for consistency with the Python engine but not benchmarked.'],
  ['Popular titles only.', 'The catalogue is the most popular non-adult titles on AniList and the best-voted movies and series on IMDb. Obscure works are absent, and the popularity term nudges results toward the head.'],
  ['Live action is not validated across media.', 'There are no human labels for anime to film or series. Movies and series use the same scoring and the same adapter, trained only on anime and manga edges.'],
  ['Text is English only.', 'Plot text and themes come from AniList descriptions and English Wikipedia leads. Titles in other languages are matched by their romanised names.'],
  ['No language model in the loop.', 'A large language model re-ranker would need a hosted key and a server, which this free static site deliberately avoids. It was not tried, so nothing here says whether it would help.'],
  ['Harness change after the first look.', 'After the first validation run, with the test split untouched, the fusion grid gained a centring switch, two ablation rows were added and the encoder is chosen by validation score of the full system. The pre-registration file and the run notes record this.'],
]
}

export function Limits({ ev }: { ev: Evidence | null }) {
  return (
    <section id="limits" aria-labelledby="lim-h">
      <h2 id="lim-h">Where it breaks, and what was not tried.</h2>
      <ul className="limits">
        {limits(ev).map(([a, b]) => (
          <li key={a}><strong>{a}</strong><span>{b}</span></li>
        ))}
      </ul>
    </section>
  )
}

export function Foot() {
  return (
    <footer className="foot">
      <div>
        <p>
          Kindred is an unofficial, non-commercial portfolio project. Anime and manga data from the AniList API (not affiliated with AniList);
          movie and series lists from the IMDb non-commercial datasets and Wikidata; text signals computed from Wikipedia (CC BY-SA); MovieLens
          25M from GroupLens for the sanity check. Cover art is loaded from AniList at display time. Nothing you type leaves your browser.
        </p>
        <p>
          <a href="https://github.com/brej-29/recai-personalization-engine">Source, benchmark code and pre-registration</a>
        </p>
      </div>
    </footer>
  )
}

const mb = (b: number) => (b / 1e6).toFixed(1)

export function HowItRuns({ ev }: { ev: Evidence | null }) {
  const total = ev ? Object.values(ev.payload.bytes).reduce((a, b) => a + b, 0) : 0
  const steps: [string, string][] = [
    ['Collect', `A bounded, rate-limited AniList pull (${ev ? ev.silo.titles.toLocaleString() : ''} titles), IMDb datasets and Wikipedia leads for ${ev ? (ev.payload.n - ev.silo.titles).toLocaleString() : ''} movies and series. Raw data stays out of the repository.`],
    ['Learn', 'gte-small sentence embeddings, then a linear adapter trained with a contrastive loss on same-medium recommendation edges only, with every edge touching a validation or test franchise removed.'],
    ['Pack', ev ? `Titles, a ${ev.payload.d}-number taste vector per title, a sparse tag channel and popularity priors: ${mb(total)} MB of static files.` : 'Static files.'],
    ['Serve', 'GitHub Pages. The browser ranks every title against your seeds, so there is no server to sleep, no quota to run out and nothing you type leaves the page.'],
  ]
  return (
    <section id="how" aria-labelledby="how-h">
      <h2 id="how-h">Built to cost nothing and never go to sleep.</h2>
      <ol className="steps">
        {steps.map(([a, b]) => (
          <li key={a}><strong>{a}</strong><span>{b}</span></li>
        ))}
      </ol>
      <p className="note">
        The Python engine that was benchmarked and the TypeScript engine in this page are tested against each other on the shipped files, so the numbers above describe what runs here.
      </p>
    </section>
  )
}
