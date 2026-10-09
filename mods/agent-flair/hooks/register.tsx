import { atom, read, update } from 'claude-code'
import type { Register } from 'claude-code'

type Look = {
  body: string
  accent: string
  dark: string
  hat: 'none' | 'hardhat' | 'wizard' | 'crown' | 'helmet' | 'antenna' | 'goggles'
  eyes: 'dots' | 'scan'
  gait: 'walk' | 'pace' | 'stomp' | 'still'
  arms: 'wave' | 'raise' | 'hammer' | 'march'
  prop: 'none' | 'wrench' | 'sparkle' | 'shield'
}

type Style = { glyph: string; title: string; color: string; border: string; spawn: string; look: Look }

const STYLES: Record<string, Style> = {
  Explore: {
    glyph: '◎', title: 'SCOUT', color: '#38bdf8', border: 'round', spawn: 'radar sweep',
    look: { body: '#38bdf8', accent: '#fde047', dark: '#0c4a6e', hat: 'none', eyes: 'scan', gait: 'walk', arms: 'wave', prop: 'none' },
  },
  Plan: {
    glyph: '◈', title: 'ARCHITECT', color: '#a78bfa', border: 'double', spawn: 'drafting blueprint',
    look: { body: '#a78bfa', accent: '#fbbf24', dark: '#4c1d95', hat: 'hardhat', eyes: 'dots', gait: 'pace', arms: 'hammer', prop: 'none' },
  },
  'general-purpose': {
    glyph: '✦', title: 'OPERATIVE', color: '#fbbf24', border: 'bold', spawn: 'deploying',
    look: { body: '#fbbf24', accent: '#ef4444', dark: '#78350f', hat: 'antenna', eyes: 'dots', gait: 'stomp', arms: 'march', prop: 'none' },
  },
  'claude-code-guide': {
    glyph: '✎', title: 'ORACLE', color: '#34d399', border: 'singleDouble', spawn: 'consulting the docs',
    look: { body: '#34d399', accent: '#fde68a', dark: '#065f46', hat: 'wizard', eyes: 'dots', gait: 'still', arms: 'raise', prop: 'sparkle' },
  },
  'statusline-setup': {
    glyph: '▤', title: 'TINKERER', color: '#f472b6', border: 'dashed', spawn: 'wiring the status line',
    look: { body: '#f472b6', accent: '#cbd5e1', dark: '#831843', hat: 'goggles', eyes: 'dots', gait: 'still', arms: 'hammer', prop: 'wrench' },
  },
  claude: {
    glyph: '❖', title: 'CLAUDE', color: '#fb923c', border: 'round', spawn: 'standing up',
    look: { body: '#d97757', accent: '#fde047', dark: '#7c2d12', hat: 'crown', eyes: 'dots', gait: 'walk', arms: 'wave', prop: 'none' },
  },
}

const FALLBACK: Style = {
  glyph: '⬡', title: 'AGENT', color: '#94a3b8', border: 'single', spawn: 'spinning up',
  look: { body: '#94a3b8', accent: '#e2e8f0', dark: '#334155', hat: 'none', eyes: 'dots', gait: 'walk', arms: 'wave', prop: 'none' },
}

// Agents from plugins (cockroachdb:...) share a family look, keyed by prefix.
const FAMILIES: Record<string, Style> = {
  cockroachdb: {
    glyph: '⌬', title: 'DB-WARDEN', color: '#6366f1', border: 'classic', spawn: 'tuning the cluster',
    look: { body: '#6366f1', accent: '#e2e8f0', dark: '#1e1b4b', hat: 'helmet', eyes: 'dots', gait: 'stomp', arms: 'march', prop: 'shield' },
  },
}

const styleFor = (type: string | undefined): Style => {
  if (type === undefined) return STYLES['general-purpose']!
  return STYLES[type] ?? FAMILIES[type.split(':')[0]!] ?? FALLBACK
}

// Claw'd, as a 9x8 pixel grid (about 9 columns by 4 rows of text):
// O body, A accent, B dark, K eye, W white, . empty.
const W = 9
const H = 8
const EYE = '#141414'

const clawd = (t: number, isMoving: boolean, look: Look): string[] => {
  const g = Array.from({ length: H }, () => Array<string>(W).fill('.'))
  const set = (r: number, c: number, v: string) => {
    if (r >= 0 && r < H && c >= 0 && c < W) g[r]![c] = v
  }
  const fill = (r: number, c0: number, c1: number, v = 'O') => {
    for (let c = c0; c <= c1; c++) set(r, c, v)
  }

  // Head, body.
  fill(2, 1, 7)
  fill(3, 1, 7)
  fill(4, 1, 7)
  fill(5, 1, 7)

  // Arms: two pixels tall, raised by one row.
  const n = isMoving ? t : 0
  let leftUp = false
  let rightUp = false
  if (isMoving) {
    if (look.arms === 'wave') {
      leftUp = n % 4 === 1
      rightUp = n % 4 === 3
    } else if (look.arms === 'raise') {
      leftUp = rightUp = n % 4 < 2
    } else if (look.arms === 'hammer') {
      rightUp = n % 2 === 0
    } else {
      leftUp = n % 2 === 0
      rightUp = n % 2 === 1
    }
  }
  const leftTop = leftUp ? 2 : 3
  const rightTop = rightUp ? 2 : 3
  for (let r = leftTop; r < leftTop + 2; r++) set(r, 0, look.prop === 'shield' ? 'A' : 'O')
  for (let r = rightTop; r < rightTop + 2; r++) set(r, 8, 'O')
  if (look.prop === 'shield') set(4, 1, 'A')

  // Eyes.
  const isBlink = isMoving && n % 12 === 6
  if (!isBlink) {
    if (look.eyes === 'scan') {
      const shift = [0, 1, 0, -1][n % 4]!
      set(3, 2 + shift, 'K')
      set(3, 6 + shift, 'K')
      set(2, 2, 'B')
      set(2, 6, 'B')
    } else {
      set(3, 2, 'K')
      set(3, 6, 'K')
    }
  }

  // Hat.
  switch (look.hat) {
    case 'hardhat':
      set(0, 4, 'A')
      fill(1, 3, 5, 'A')
      fill(2, 1, 7, 'A')
      break
    case 'wizard':
      set(0, 4, isMoving && n % 2 === 0 ? 'A' : 'B')
      fill(1, 3, 5, 'B')
      fill(2, 1, 7, 'B')
      break
    case 'crown':
      for (const c of [2, 4, 6]) set(1, c, 'A')
      fill(2, 2, 6, 'A')
      break
    case 'helmet':
      set(0, 4, 'A')
      fill(1, 2, 6, 'B')
      fill(2, 1, 7, 'B')
      break
    case 'antenna':
      set(0, 4, isMoving && n % 2 === 0 ? 'A' : 'B')
      set(1, 4, 'B')
      break
    case 'goggles':
      fill(2, 1, 7, 'B')
      set(1, 2, 'W')
      set(1, 6, 'W')
      break
    default:
      break
  }

  // Props.
  if (look.prop === 'wrench') {
    set(rightTop - 1, 8, 'A')
  } else if (look.prop === 'sparkle' && isMoving) {
    const [r, c] = [[0, 1], [0, 7], [1, 8], [1, 0]][n % 4]!
    set(r!, c!, 'A')
  }

  // Legs: four of them; the gait decides how they lift.
  let lift = 0
  if (isMoving) {
    if (look.gait === 'walk') lift = n % 4
    else if (look.gait === 'pace') lift = (n >> 1) % 4
    else if (look.gait === 'stomp') lift = n % 2 === 0 ? 1 : 3
  }
  const legs: [number[], boolean][] = [
    [[1], true],
    [[3], false],
    [[5], false],
    [[7], true],
  ]
  for (const [cols, isOuter] of legs) {
    const isLifted = (isOuter && lift === 1) || (!isOuter && lift === 3)
    const len = isLifted ? 1 : 2
    for (let r = 6; r < 6 + len; r++) for (const c of cols) set(r, c, 'O')
  }

  return g.map(row => row.join(''))
}

type Run = { text: string; fg?: string; bg?: string }

// Two pixel rows per text row, using half blocks.
const toRuns = (grid: string[], look: Look): Run[][] => {
  const palette: Record<string, string> = { O: look.body, A: look.accent, B: look.dark, K: EYE, W: '#f5f5f5' }
  const color = (p: string) => palette[p]!
  const lines: Run[][] = []
  for (let j = 0; j < H; j += 2) {
    const runs: Run[] = []
    for (let i = 0; i < W; i++) {
      const top = grid[j]![i]!
      const bot = grid[j + 1]![i]!
      let cell: Run
      if (top === bot) {
        cell = top === '.' ? { text: ' ' } : { text: '█', fg: color(top) }
      } else if (top === '.') {
        cell = { text: '▄', fg: color(bot) }
      } else if (bot === '.') {
        cell = { text: '▀', fg: color(top) }
      } else {
        cell = { text: '▀', fg: color(top), bg: color(bot) }
      }
      const prev = runs[runs.length - 1]
      if (prev && prev.fg === cell.fg && prev.bg === cell.bg) prev.text += cell.text
      else runs.push(cell)
    }
    lines.push(runs)
  }
  return lines
}

const frame = atom({ plugin: 'agent-flair', key: 'frame' } as const, 0)

export const register: Register = on => {
  // Rows of agents still working: Claw'd only moves while this is non-empty.
  const running = new Set<string>()

  on('session.start', ($, e, next) => {
    $.clock.every(200, () => {
      if (running.size > 0) void update($, frame, n => ((n ?? 0) + 1) % 1200)
    })

    return next(e)
  })

  on('agent.spawn', ($, e, next) => {
    const s = styleFor(e.subagentType)
    $.ui.toast(`${s.glyph} ${s.title} ${s.spawn}…`)

    return next(e)
  })

  on('ui.render', { component: 'ToolUse', props: { tool: 'Agent' } }, async ($, e, next) => {
    const input = e.props.input as { subagent_type?: string; description?: string; name?: string }
    const s = styleFor(input.subagent_type)
    const { Box, Text } = $.ui.resolve(e)

    const isWorking = e.props.isRunning && !e.props.isErrored
    if (isWorking) running.add(e.requestId)
    else running.delete(e.requestId)

    const t = isWorking ? await read($, frame) : 0
    const lines = toRuns(clawd(t, isWorking, s.look), s.look)

    const state = e.props.isErrored ? '✗ failed' : e.props.isRunning ? '⟳ working' : '✓ done'
    const stateColor = e.props.isErrored ? '#f87171' : e.props.isRunning ? s.color : '#4ade80'

    return (
      <Box borderStyle={s.border} borderColor={s.color} paddingX={1} gap={2}>
        <Box flexDirection="column">
          {lines.map((runs, i) => (
            <Box key={`l${i}`}>
              {runs.map((r, k) => (
                <Text key={`r${k}`} color={r.fg} backgroundColor={r.bg}>
                  {r.text}
                </Text>
              ))}
            </Box>
          ))}
        </Box>
        <Box flexDirection="column" justifyContent="center">
          <Box gap={1}>
            <Text color={s.color} bold>
              {s.glyph} {s.title}
            </Text>
            <Text dimColor>{input.subagent_type ?? 'general-purpose'}</Text>
            {input.name ? <Text italic>“{input.name}”</Text> : ''}
            <Text color={stateColor}>{state}</Text>
          </Box>
          <Text>{input.description ?? ''}</Text>
        </Box>
      </Box>
    )
  })
}
