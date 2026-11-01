import { Component, type ReactNode, useEffect, useId, useMemo, useRef, useState } from 'react'
import { Atlas } from './Atlas'
import { type Data, MEDIA_CODE, MEDIA_LABEL, coverUrl, loadData, sourceUrl } from './data'
import { type Hit, readout, recommend, searchTitles } from './engine'
import { Silo as SiloSection, Test } from './Evidence'
import { Foot, HowItRuns, Limits, Sanity } from './Limits'
import { type Evidence, Scoreboard } from './Scoreboard'
import { Seg } from './Seg'

class Guard extends Component<{ children: ReactNode }, { bad: boolean }> {
  state = { bad: false }
  static getDerivedStateFromError() { return { bad: true } }
  render() {
    return this.state.bad ? <p className="empty" role="alert">This section failed to render. The console above still works.</p> : this.props.children
  }
}

const DEMO = ['Frieren', 'Solo Leveling', 'Parasite', 'Death Note', 'Berserk']
const MAX_SEEDS = 5
const mc = (m: number) => ({ ['--mc' as string]: `var(--m${m})` })

function useSkin() {
  const [skin, setSkin] = useState<'led' | 'lcd'>(() => {
    try {
      const s = localStorage.getItem('kindred-skin')
      if (s === 'led' || s === 'lcd') return s
    } catch {
      /* storage blocked */
    }
    return matchMedia('(prefers-color-scheme: light)').matches ? 'lcd' : 'led'
  })
  useEffect(() => {
    document.documentElement.dataset.skin = skin
    try {
      localStorage.setItem('kindred-skin', skin)
    } catch {
      /* storage blocked */
    }
  }, [skin])
  return [skin, setSkin] as const
}

export default function App() {
  const [data, setData] = useState<Data | null>(null)
  const [err, setErr] = useState(false)
  const [ev, setEv] = useState<Evidence | null>(null)
  const [skin, setSkin] = useSkin()
  useEffect(() => {
    loadData().then(setData).catch(() => setErr(true))
    fetch(import.meta.env.BASE_URL + 'data/evidence.json').then((r) => r.json()).then(setEv).catch(() => setEv(null))
  }, [])

  return (
    <>
      <a className="skip" href="#console">Skip to the console</a>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Kindred">
          <Seg text="KINDRED" className="glow" />
        </a>
        <nav aria-label="Sections">
          <a href="#silo">The silo</a>
          <a className="keep" href="#scoreboard">Scoreboard</a>
          <a href="#limits">Limits</a>
          <a className="keep" href="https://github.com/brej-29/recai-personalization-engine">Source</a>
          <div className="skin" role="group" aria-label="Display skin">
            <button aria-pressed={skin === 'led'} onClick={() => setSkin('led')}>LED</button>
            <button aria-pressed={skin === 'lcd'} onClick={() => setSkin('lcd')}>LCD</button>
          </div>
        </nav>
      </header>
      <main id="top">
        {err ? <p className="empty" role="alert">Could not load the catalogue. Reload to retry.</p> : <Console data={data} silo={ev?.silo ?? null} />}
        <div className="story">
          <Guard><SiloSection silo={ev?.silo ?? null} /></Guard>
          <Guard><Test /></Guard>
          <Guard><Scoreboard ev={ev} /></Guard>
          <Guard><Sanity ev={ev} /></Guard>
          <Guard><Limits ev={ev} /></Guard>
          <Guard><HowItRuns ev={ev} /></Guard>
        </div>
      </main>
      <Foot />
    </>
  )
}

function Console({ data, silo }: { data: Data | null; silo: Evidence['silo'] | null }) {
  const [seeds, setSeeds] = useState<number[]>([])
  const [media, setMedia] = useState<number | null>(null)
  const [hideF, setHideF] = useState(true)
  const [demoIdx, setDemoIdx] = useState(0)
  const [touched, setTouched] = useState(false)
  const [paused, setPaused] = useState(false)

  const demoSeeds = useMemo(() => {
    if (!data) return []
    return DEMO.map((q) => searchTitles(data, q, 1)[0]).filter((x) => x !== undefined)
  }, [data])

  useEffect(() => {
    if (touched || paused || !demoSeeds.length || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setDemoIdx((i) => (i + 1) % demoSeeds.length), 6500)
    return () => clearInterval(id)
  }, [touched, paused, demoSeeds])

  const active = touched ? seeds : demoSeeds.length ? [demoSeeds[demoIdx]] : []
  const key = active.join(',')
  const { hits, ms } = useMemo(() => {
    if (!data || !active.length) return { hits: [] as Hit[], ms: 0 }
    const t0 = performance.now()
    const h = recommend(data, active, { media, hideFranchise: hideF, k: 12 })
    return { hits: h, ms: performance.now() - t0 }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, key, media, hideF])

  const add = (i: number) => {
    setTouched(true)
    setSeeds((s) => (s.includes(i) || s.length >= MAX_SEEDS ? s : [...s, i]))
  }
  const remove = (i: number) => {
    setTouched(true)
    setSeeds((s) => s.filter((x) => x !== i))
  }

  return (
    <div className="console" id="console" onPointerEnter={() => setPaused(true)} onPointerLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)}>
      <Rail silo={silo} data={data} seeds={touched ? seeds : []} demo={!touched ? active : []} add={add} remove={remove}
        media={media} setMedia={setMedia} hideF={hideF} setHideF={setHideF} />
      <Board data={data} hits={hits} active={active} demo={!touched} media={media} ms={ms} />
      {data && <Atlas data={data} seeds={active} hits={hits} media={media} />}
    </div>
  )
}

function Rail(props: {
  silo: Evidence['silo'] | null; data: Data | null; seeds: number[]; demo: number[]; add: (i: number) => void; remove: (i: number) => void
  media: number | null; setMedia: (m: number | null) => void; hideF: boolean; setHideF: (b: boolean) => void
}) {
  const { data, seeds, add, remove, media, setMedia, hideF, setHideF } = props
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [cur, setCur] = useState(0)
  const lid = useId()
  const sugg = useMemo(() => (data ? searchTitles(data, q, 7) : []), [data, q])
  const input = useRef<HTMLInputElement>(null)

  const pick = (i: number) => {
    add(i)
    setQ('')
    setOpen(false)
    input.current?.focus()
  }
  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setCur((c) => Math.min(c + 1, sugg.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setCur((c) => Math.max(c - 1, 0)) }
    else if (e.key === 'Enter' && open && sugg[cur] !== undefined) { e.preventDefault(); pick(sugg[cur]) }
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <section className="rail" aria-labelledby="h1">
      <h1 id="h1">One title in. <em>Kin</em> in every medium.</h1>
      <p className="lede">Anime, manga, manhwa, manhua, novels, films and series share no ratings, so no site can connect them. Kindred reads what each title is about and finds its kin.</p>

      <div className="field">
        <label className="label" htmlFor={lid}>Name something you loved</label>
        <input id={lid} ref={input} value={q} autoComplete="off" disabled={!data}
          placeholder={data ? 'Try Frieren, Solo Leveling, Parasite' : 'Loading the catalogue'}
          role="combobox" aria-expanded={open && sugg.length > 0} aria-controls={lid + '-l'} aria-autocomplete="list"
          aria-activedescendant={open && sugg.length ? `${lid}-o${cur}` : undefined}
          onChange={(e) => { setQ(e.target.value); setOpen(true); setCur(0) }}
          onKeyDown={onKey} onBlur={() => setTimeout(() => setOpen(false), 120)} onFocus={() => setOpen(true)} />
        {open && data && sugg.length > 0 && (
          <ul className="sugg" role="listbox" id={lid + '-l'}>
            {sugg.map((i, n) => (
              <li key={i} id={`${lid}-o${n}`} role="option" aria-selected={n === cur}
                onMouseDown={(e) => { e.preventDefault(); pick(i) }}>
                <span className="chip" style={mc(data.cat.m[i])}>{MEDIA_CODE[data.cat.m[i]]}</span>
                <span className="t">{data.cat.t[i]}</span>
                <span className="label">{data.cat.y[i] || ''}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div>
        <div className="label" style={{ marginBottom: 8 }}>Seeds, up to {MAX_SEEDS}</div>
        <div className="slots">
          {Array.from({ length: Math.min(MAX_SEEDS, seeds.length + 1) }, (_, n) => {
            const i = seeds[n]
            return i !== undefined && data ? (
              <div className="slot full" key={n}>
                <Seg text={String(n + 1)} />
                <span className="n">{data.cat.t[i]}</span>
                <button onClick={() => remove(i)} aria-label={`Remove ${data.cat.t[i]}`}>REMOVE</button>
              </div>
            ) : (
              <div className="slot" key={n}>
                <Seg text={String(n + 1)} className="ghosted" />
                <span>{n === 0 && !seeds.length && props.demo.length && data ? `Demo: ${data.cat.t[props.demo[0]]}` : 'Empty'}</span>
                <span />
              </div>
            )
          })}
        </div>
      </div>

      <div>
        <div className="label" style={{ marginBottom: 8 }}>Shelf</div>
        <div className="lamps" role="group" aria-label="Filter results by medium">
          <button className="lamp all" aria-pressed={media === null} onClick={() => setMedia(null)}>
            <i /><span>All media, diversified</span>
          </button>
          {MEDIA_LABEL.map((l, m) => (
            <button key={l} className="lamp" style={mc(m)} aria-pressed={media === m} onClick={() => setMedia(media === m ? null : m)}>
              <i /><span>{l}</span>
            </button>
          ))}
        </div>
      </div>
      {props.silo && (
        <a className="silo-link" href="#silo">
          <span>AniList user links from anime to manga or novels:</span>
          <Seg text={String(props.silo.rec_edges_anime_to_print_or_back)} className="glow" label={`${props.silo.rec_edges_anime_to_print_or_back}`} />
          <span>of {props.silo.rec_edges_same_format.toLocaleString()}. Why it matters</span>
        </a>
      )}
      <button className="toggle" aria-pressed={hideF} onClick={() => setHideF(!hideF)}>
        <i /><span>Hide the same franchise (sequels, adaptations)</span>
      </button>
    </section>
  )
}

function Board({ data, hits, active, demo, media, ms }: {
  data: Data | null; hits: Hit[]; active: number[]; demo: boolean; media: number | null; ms: number
}) {
  const cos = readout(hits)
  return (
    <section className="board" aria-labelledby="board-h" aria-live="polite">
      <div className="board-head">
        <h2 className="label" id="board-h">{media === null ? 'Kin across all media' : `Kin in ${MEDIA_LABEL[media].toLowerCase()}`}</h2>
        <span className={`label status ${demo ? 'demo' : ''}`}>
          <i />{!data ? 'Warming up' : demo ? 'Demo' : `${active.length} seed${active.length > 1 ? 's' : ''}`}
        </span>
      </div>
      {data && active.length > 0 && (
        <p className="because">Because you loved <strong>{active.map((i) => data.cat.t[i]).join(', ')}</strong></p>
      )}
      {!data && (
        <ol className="rows loading" aria-label="Loading">
          {Array.from({ length: 12 }, (_, n) => (
            <li className="row" key={n}>
              <Seg text="88" className="rank ghosted" /><span className="cover" /><span /><Seg text="88" className="cos ghosted" />
            </li>
          ))}
        </ol>
      )}
      {data && !hits.length && <p className="empty">Nothing to show yet. Name a title you loved, in any medium.</p>}
      {data && hits.length > 0 && (
        <ol className="rows">
          {hits.map((h, n) => {
            const m = data.cat.m[h.i]
            const img = coverUrl(data.cat, h.i)
            return (
              <li className="row" key={n} style={mc(m)}>
                <Seg text={String(n + 1).padStart(2, '0')} className="rank" label={`Rank ${n + 1}`} />
                <span className="cover" aria-hidden="true">
                  <span className="tile">{data.cat.t[h.i].slice(0, 22)}</span>
                  {img && <img src={img} alt="" loading="lazy" decoding="async" onError={(e) => (e.currentTarget.style.display = 'none')} />}
                </span>
                <div className="meta">
                  <a className="t" href={sourceUrl(data.cat, h.i)} target="_blank" rel="noreferrer">{data.cat.t[h.i]}</a>
                  <div className="sub">
                    <span className="chip">{MEDIA_LABEL[m]}</span>
                    {data.cat.y[h.i] > 0 && <span>{data.cat.y[h.i]}</span>}
                    <span className="why">{h.why.length ? `Shares ${h.why.join(', ')}` : 'Close in plot and tone'}</span>
                  </div>
                </div>
                <Seg text={String(cos[n])} className="cos glow" label={`Cosine similarity ${cos[n]} out of 100`} />
              </li>
            )
          })}
        </ol>
      )}
      <p className="note">
        Readout is the cosine similarity x 100 in the taste space, not a probability; rank also uses shared themes and popularity.
        {data && hits.length > 0 ? ` Ranked ${data.cat.n.toLocaleString()} titles in ${ms < 10 ? ms.toFixed(1) : Math.round(ms)} ms, in your browser.` : ''}
        {demo ? ' Type a title to take over from the demo.' : ''}
      </p>
    </section>
  )
}
