import { memo } from 'react'

// One eight-cell mask draws every glyph. Unlit segments are drawn too (ghost cells).
// 14-segment names: a top, b upper-right, c lower-right, d bottom, e lower-left, f upper-left,
// g middle-left, G middle-right, h/j upper diagonals, k/m lower diagonals, i/l centre verticals.
const MAP: Record<string, string> = {
  '0': 'abcdef', '1': 'bc', '2': 'abdegG', '3': 'abcdgG',
  '4': 'bcfgG', '5': 'acdfgG', '6': 'acdefgG', '7': 'abc', '8': 'abcdefgG', '9': 'abcdfgG',
  A: 'abcefgG', B: 'abcdGil', C: 'adef', D: 'abcdil', E: 'adefgG', F: 'aefgG', G: 'acdefG',
  H: 'bcefgG', I: 'adil', J: 'bcde', K: 'efgjm', L: 'def', M: 'bcefhj', N: 'bcefhm',
  O: 'abcdef', P: 'abefgG', Q: 'abcdefm', R: 'abefgGm', S: 'acdfgG', T: 'ail', U: 'bcdef',
  V: 'efjk', W: 'bcefkm', X: 'hjkm', Y: 'hjl', Z: 'adjk', '-': 'gG', '+': 'gGil', '/': 'jk',
  '%': 'hjkm', ' ': '', '_': 'd',
}
const W = 56
const H = 96
const T = 9 // bar thickness
const GAP = 2.2

function hbar(x1: number, x2: number, y: number) {
  const h = T / 2
  return `${x1},${y} ${x1 + h},${y - h} ${x2 - h},${y - h} ${x2},${y} ${x2 - h},${y + h} ${x1 + h},${y + h}`
}
function vbar(y1: number, y2: number, x: number) {
  const h = T / 2
  return `${x},${y1} ${x + h},${y1 + h} ${x + h},${y2 - h} ${x},${y2} ${x - h},${y2 - h} ${x - h},${y1 + h}`
}
const mx = W / 2
const my = H / 2
const L = T / 2 + 1
const R = W - T / 2 - 1
const TOP = T / 2 + 1
const BOT = H - T / 2 - 1
const g = GAP

const POLY: Record<string, string> = {
  a: hbar(L + T / 2 + g, R - T / 2 - g, TOP),
  d: hbar(L + T / 2 + g, R - T / 2 - g, BOT),
  g: hbar(L + T / 2 + g, mx - g, my),
  G: hbar(mx + g, R - T / 2 - g, my),
  b: vbar(TOP + T / 2 + g, my - g, R),
  c: vbar(my + g, BOT - T / 2 - g, R),
  e: vbar(my + g, BOT - T / 2 - g, L),
  f: vbar(TOP + T / 2 + g, my - g, L),
  i: vbar(TOP + T / 2 + g, my - g, mx),
  l: vbar(my + g, BOT - T / 2 - g, mx),
}
const DIAG: Record<string, [number, number, number, number]> = {
  h: [L + 7, TOP + 11, mx - 6, my - 9],
  j: [R - 7, TOP + 11, mx + 6, my - 9],
  k: [L + 7, BOT - 11, mx - 6, my + 9],
  m: [R - 7, BOT - 11, mx + 6, my + 9],
}
const ALL = [...Object.keys(POLY), ...Object.keys(DIAG)]
const SEVEN = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'G'] // numerals use the plain seven-segment mask, no ghost diagonals

const Cell = memo(function Cell({ ch }: { ch: string }) {
  const on = new Set((MAP[ch.toUpperCase()] ?? '').split(''))
  if (ch === '.') {
    return (
      <svg viewBox={`0 0 ${W * 0.4} ${H}`} className="seg-cell seg-narrow" aria-hidden="true">
        <rect x={W * 0.12} y={H - 16} width={11} height={11} className="seg on" />
      </svg>
    )
  }
  if (ch === ',') {
    return (
      <svg viewBox={`0 0 ${W * 0.4} ${H}`} className="seg-cell seg-narrow" aria-hidden="true">
        <rect x={W * 0.12} y={H - 16} width={11} height={11} className="seg on" />
        <rect x={W * 0.12 - 3} y={H - 6} width={7} height={9} className="seg on" />
      </svg>
    )
  }
  if (ch === ':') {
    return (
      <svg viewBox={`0 0 ${W * 0.4} ${H}`} className="seg-cell seg-narrow" aria-hidden="true">
        <rect x={W * 0.12} y={my - 22} width={11} height={11} className="seg on" />
        <rect x={W * 0.12} y={my + 12} width={11} height={11} className="seg on" />
      </svg>
    )
  }
  const keys = /[0-9-]/.test(ch) ? SEVEN : ALL
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="seg-cell" aria-hidden="true">
      {keys.map((k) => (
        <g key={k} className={on.has(k) ? 'seg on' : 'seg'}>
          {POLY[k] ? <polygon points={POLY[k]} /> : (
            <line x1={DIAG[k][0]} y1={DIAG[k][1]} x2={DIAG[k][2]} y2={DIAG[k][3]} strokeWidth={T - 1.5} />
          )}
        </g>
      ))}
    </svg>
  )
})

type Props = { text: string; label?: string; className?: string; pad?: number }

/** Segment display. `label` is the accessible text; glyphs are decorative. */
export function Seg({ text, label, className = '', pad = 0 }: Props) {
  const s = text.padStart(pad, ' ')
  return (
    <span className={`seg-text ${className}`} role="img" aria-label={label ?? text.trim()}>
      {[...s].map((ch, i) => <Cell key={i} ch={ch} />)}
    </span>
  )
}
