import { useEffect, useRef, useState } from 'react'
import type { Data } from './data'
import { MEDIA_CODE, MEDIA_LABEL } from './data'
import type { Hit } from './engine'

type Props = { data: Data; seeds: number[]; hits: Hit[]; media: number | null }

function medianCentres(data: Data): ([number, number] | null)[] {
  const xs: number[][] = Array.from({ length: 8 }, () => [])
  const ys: number[][] = Array.from({ length: 8 }, () => [])
  for (let i = 0; i < data.cat.n; i++) { xs[data.cat.m[i]].push(data.xy[i * 2]); ys[data.cat.m[i]].push(data.xy[i * 2 + 1]) }
  const med = (a: number[]) => a.slice().sort((p, q) => p - q)[a.length >> 1]
  return xs.map((x, m) => (x.length ? [med(x), med(ys[m])] : null))
}

const css = (n: string) => getComputedStyle(document.documentElement).getPropertyValue(n).trim()

/** Dot-matrix map of the whole catalogue. Seeds ignite, kin are joined by arcs. */
export function Atlas({ data, seeds, hits, media }: Props) {
  const seedsKey = seeds.join(',')
  const ref = useRef<HTMLCanvasElement>(null)
  const [tip, setTip] = useState<number | null>(null)
  const anim = useRef(0)

  useEffect(() => {
    const cv = ref.current!
    const ctx = cv.getContext('2d')!
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches
    let raf = 0
    const hues = Array.from({ length: 8 }, (_, m) => css('--m' + m))
    const hue = (m: number) => hues[m]
    const ghost = css('--ghost-2')
    const ghostDim = css('--ghost')
    const litC = css('--lit')
    const textC = css('--text')
    const start = performance.now()
    const centroids = medianCentres(data)
    const seedKey = seeds.join(',')
    void seedKey
    const draw = (now: number) => {
      const dpr = Math.min(devicePixelRatio || 1, 2)
      const { clientWidth: w, clientHeight: h } = cv
      if (cv.width !== w * dpr || cv.height !== h * dpr) { cv.width = w * dpr; cv.height = h * dpr }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)
      const pad = 28
      const X = (i: number) => pad + data.xy[i * 2] * (w - pad * 2)
      const Y = (i: number) => pad + data.xy[i * 2 + 1] * (h - pad * 2)
      const t = reduce ? 1 : Math.min(1, (now - start) / 700)
      const e = 1 - Math.pow(1 - t, 4)
      const active = media === null ? null : media
      const hot = hits.length > 0
      for (let i = 0; i < data.cat.n; i++) {
        const m = data.cat.m[i]
        const on = active === null ? true : m === active
        ctx.fillStyle = on ? (hot ? ghost : hue(m)) : ghostDim
        ctx.globalAlpha = on ? (hot ? 0.9 : 0.55) : 0.5
        ctx.fillRect(X(i), Y(i), 1.6, 1.6)
      }
      ctx.globalAlpha = 1
      ctx.font = '600 11px "Barlow Condensed", sans-serif'
      ctx.textAlign = 'center'
      for (let m = 0; m < 8; m++) {
        if (active !== null && m !== active) continue
        const c = centroids[m]
        if (!c) continue
        ctx.fillStyle = hue(m)
        ctx.fillText(MEDIA_CODE[m].split('').join(' '), pad + c[0] * (w - pad * 2), pad + c[1] * (h - pad * 2) - 10)
      }
      for (const h2 of hits) {
        const m = data.cat.m[h2.i]
        ctx.fillStyle = hue(m)
        ctx.fillRect(X(h2.i) - 2.5, Y(h2.i) - 2.5, 5, 5)
        for (const s of seeds) {
          const x0 = X(s), y0 = Y(s), x1 = x0 + (X(h2.i) - x0) * e, y1 = y0 + (Y(h2.i) - y0) * e
          const cx = (x0 + X(h2.i)) / 2, cy = Math.min(y0, Y(h2.i)) - 30
          ctx.strokeStyle = hue(m)
          ctx.globalAlpha = 0.35
          ctx.lineWidth = 1
          ctx.beginPath()
          ctx.moveTo(x0, y0)
          ctx.quadraticCurveTo(cx + (x1 - x0) * 0, cy, x1, y1)
          ctx.stroke()
          ctx.globalAlpha = 1
        }
      }
      for (const s of seeds) {
        ctx.fillStyle = litC
        ctx.fillRect(X(s) - 4, Y(s) - 4, 8, 8)
        ctx.strokeStyle = textC
        ctx.lineWidth = 1.5
        ctx.strokeRect(X(s) - 7, Y(s) - 7, 14, 14)
      }
      if (t < 1) raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    anim.current = raf
    const ro = new ResizeObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw) })
    ro.observe(cv)
    const mo = new MutationObserver(() => { cancelAnimationFrame(raf); raf = requestAnimationFrame(draw) })
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-skin'] })
    return () => { cancelAnimationFrame(raf); ro.disconnect(); mo.disconnect() }
  }, [data, seedsKey, hits, media])

  const onMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const cv = ref.current!
    const r = cv.getBoundingClientRect()
    const pad = 28
    const px = (e.clientX - r.left - pad) / (r.width - pad * 2)
    const py = (e.clientY - r.top - pad) / (r.height - pad * 2)
    let best = -1, bd = 0.0004
    for (let i = 0; i < data.cat.n; i++) {
      if (media !== null && data.cat.m[i] !== media) continue
      const dx = data.xy[i * 2] - px, dy = data.xy[i * 2 + 1] - py
      const d = dx * dx + dy * dy
      if (d < bd) { bd = d; best = i }
    }
    setTip(best < 0 ? null : best)
  }

  return (
    <aside className="atlas" aria-label="Map of the catalogue">
      <div className="atlas-sticky">
        <div className="label"><span>Atlas</span><span>{data.cat.n.toLocaleString()} titles</span></div>
        <canvas ref={ref} onPointerMove={onMove} onPointerLeave={() => setTip(null)} role="img"
          aria-label="Scatter map of every title, placed by text similarity. Selected titles are outlined and joined to their closest kin." />
        <div className="legend" aria-label="Medium codes">
          {MEDIA_CODE.map((c, m) => (
            <span key={c} style={{ ['--mc' as string]: `var(--m${m})` }}><b>{c}</b>{MEDIA_LABEL[m]}</span>
          ))}
        </div>
        <div className="tip" aria-hidden="true">
          {tip !== null && (<>
            <span className="chip" style={{ ['--mc' as string]: `var(--m${data.cat.m[tip]})` }}>{MEDIA_CODE[data.cat.m[tip]]}</span>
            <span>{data.cat.t[tip]}</span>
          </>)}
        </div>
      </div>
    </aside>
  )
}
