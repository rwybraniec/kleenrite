import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Bar, BandItem } from '../types'

const EMPTY: Bar = { items: [], planStart: null, startedAt: null, endedAt: null, tick: 0 }
const bar = atom({ plugin: 'progress-band', key: 'bar' } as const, EMPTY)

const HISTORY = 'turnMs'
const STOPS = ['#ef4444', '#f59e0b', '#22c55e'] as const

const channel = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16)

// Red at 0, amber at 0.5, green at 1.
const gradient = (x: number): string => {
  const p = Math.min(1, Math.max(0, x)) * (STOPS.length - 1)
  const lo = Math.min(STOPS.length - 2, Math.floor(p))
  const f = p - lo
  const rgb = [0, 1, 2].map(i => {
    const a = channel(STOPS[lo]!, i)
    const b = channel(STOPS[lo + 1]!, i)
    return Math.round(a + (b - a) * f)
  })

  return `#${rgb.map(v => v.toString(16).padStart(2, '0')).join('')}`
}

const duration = (ms: number): string => {
  const s = Math.max(0, Math.round(ms / 1000))
  const m = Math.floor(s / 60)

  return m > 0 ? `${m}m ${String(s % 60).padStart(2, '0')}s` : `${s}s`
}

const median = (xs: number[]): number | null => {
  if (xs.length === 0) return null
  const sorted = [...xs].sort((a, b) => a - b)

  return sorted[Math.floor(sorted.length / 2)]!
}

type View = { frac: number; label: string; eta: string; elapsed: number }

const view = (b: Bar, now: number, history: number[]): View => {
  const end = b.endedAt ?? now
  const elapsed = b.startedAt === null ? 0 : end - b.startedAt
  const isDone = b.endedAt !== null
  const total = b.items.length

  if (total > 0) {
    const done = b.items.filter(i => i.status === 'completed').length
    const active = b.items.filter(i => i.status === 'in_progress').length
    const credit = done + 0.5 * active
    const planElapsed = end - (b.planStart ?? b.startedAt ?? end)
    const isFinished = done === total
    let eta = 'estimating…'
    if (isFinished || (isDone && done === total)) eta = 'done'
    else if (credit > 0) eta = `~${duration((planElapsed * (total - credit)) / credit)} left`

    return { frac: isFinished ? 1 : credit / total, label: `${done}/${total} tasks`, eta, elapsed }
  }

  const expected = median(history)
  if (isDone) return { frac: 1, label: 'turn', eta: 'done', elapsed }
  if (expected === null) return { frac: 0.05, label: 'working', eta: 'learning your pace…', elapsed }
  const frac = Math.min(0.95, elapsed / expected)
  const eta = elapsed > expected ? 'taking longer than usual' : `~${duration(expected - elapsed)} left`

  return { frac, label: 'turn', eta, elapsed }
}

async function setItems($: EngineInterface, items: BandItem[]): Promise<void> {
  const now = await $.clock.now()
  await update($, bar, b => ({ ...b, items, planStart: b.planStart ?? now }))
  await pushStatus($)
}

const EIGHTHS = ['', '▏', '▎', '▍', '▌', '▋', '▊', '▉']


type Cell = { ch: string; color?: string }

const barCells = (frac: number, width: number): Cell[] => {
  const exact = frac * width
  const full = Math.floor(exact)
  const part = EIGHTHS[Math.floor((exact - full) * 8)]!
  const cells: Cell[] = []
  for (let i = 0; i < width; i++) {
    if (i < full) cells.push({ ch: '█', color: gradient(i / (width - 1)) })
    else if (i === full && part !== '') cells.push({ ch: part, color: gradient(i / (width - 1)) })
    else cells.push({ ch: '░' })
  }

  return cells
}

async function snapshot($: EngineInterface): Promise<{ b: Bar; v: View } | null> {
  const b = await read($, bar)
  if (b.startedAt === null && b.items.length === 0) return null
  const now = await $.clock.now()
  const history = ((await $.store.get(HISTORY)) as number[] | undefined) ?? []

  return { b, v: view(b, now, history) }
}

// A plain-text bar for surfaces that only have a status line.
async function pushStatus($: EngineInterface): Promise<void> {
  const snap = await snapshot($)
  if (snap === null) {
    $.ui.status(undefined)

    return
  }
  const { v } = snap
  const filled = Math.round(v.frac * 10)
  const text = `${'▰'.repeat(filled)}${'▱'.repeat(10 - filled)} ${Math.round(v.frac * 100)}% ${v.label} · ${duration(v.elapsed)} · ${v.eta}`
  $.ui.status(text)
}

const PANE = 'progress'

export const register: Register = on => {
  let isWorking = false
  let mainTurn: string | null = null

  on('session.start', async ($, e, next) => {
    await $.command.register({ name: 'progress', description: 'Show the task progress bar in a pane' })
    $.clock.every(1000, () => {
      if (isWorking) void update($, bar, b => ({ ...b, tick: (b.tick + 1) % 100000 })).then(() => pushStatus($))
    })

    return next(e)
  })

  on('command.run', { command: 'progress' }, async $ => {
    await $.ui.open({ id: PANE, title: 'Progress' })

    return { text: 'Progress pane opened.' }
  })

  on('prompt.submit', async ($, e, next) => {
    $.ui.open({ id: PANE, title: 'Progress' }).catch(() => undefined)
    const now = await $.clock.now()
    isWorking = true
    mainTurn = null
    await update($, bar, b => {
      const isAllDone = b.items.length > 0 && b.items.every(i => i.status === 'completed')
      const items = isAllDone ? [] : b.items

      return { ...b, items, planStart: items.length === 0 ? null : b.planStart, startedAt: now, endedAt: null }
    })

    return next(e)
  })

  on('turn.start', ($, e, next) => {
    if (mainTurn === null) mainTurn = e.turnId

    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    if (mainTurn !== null && e.turnId !== mainTurn) return next(e)
    const now = await $.clock.now()
    isWorking = false
    await update($, bar, b => ({ ...b, endedAt: now }))
    await pushStatus($)
    const old = ((await $.store.get(HISTORY)) as number[] | undefined) ?? []
    await $.store.set(HISTORY, [...old, e.durationMs].slice(-9))

    return next(e)
  })

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    const task = (ran.result as { task?: { id: string; subject: string } } | null | undefined)?.task
    if (task !== undefined) {
      const b = await read($, bar)
      const item: BandItem = { id: task.id, subject: task.subject, status: 'pending' }
      await setItems($, [...b.items.filter(i => i.id !== task.id), item])
    }

    return ran
  })

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    const result = ran.result as { success?: boolean } | null | undefined
    if (result?.success === true) {
      const b = await read($, bar)
      const status = e.status
      const items: BandItem[] =
        status === 'deleted'
          ? b.items.filter(i => i.id !== e.taskId)
          : b.items.map(i =>
              i.id === e.taskId ? { ...i, subject: e.subject ?? i.subject, status: status ?? i.status } : i,
            )
      await setItems($, items)
    }

    return ran
  })

  on('tool.call', { tool: 'TaskList' }, async ($, e, next) => {
    const ran = await next(e)
    const tasks = (ran.result as { tasks?: BandItem[] } | null | undefined)?.tasks
    if (tasks !== undefined) {
      await setItems($, tasks.map(t => ({ id: t.id, subject: t.subject, status: t.status })))
    }

    return ran
  })

  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.result !== undefined && ran.result !== null) {
      await setItems($, e.todos.map((t, i) => ({ id: `todo-${i}`, subject: t.content, status: t.status })))
    }

    return ran
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const b = await read($, bar)
    const hasPlan = b.items.length > 0
    if (e.props.hasSurvey || (b.startedAt === null && !hasPlan)) return next(e)

    const now = await $.clock.now()
    const history = ((await $.store.get(HISTORY)) as number[] | undefined) ?? []
    const v = view(b, now, history)
    const { Box, Text } = $.ui.resolve(e)

    const width = Math.max(10, Math.min(36, e.props.bodyColumns - 44))
    const cells = barCells(v.frac, width)

    const pct = Math.round(v.frac * 100)
    const head = gradient(Math.max(0, v.frac))

    return (
      <Box gap={1}>
        {cells.map((c, i) => (
          <Text key={`c${i}`} color={c.color} dimColor={c.color === undefined}>
            {c.ch}
          </Text>
        ))}
        <Text color={head} bold>
          {pct}%
        </Text>
        <Text>{v.label}</Text>
        <Text dimColor>
          · {duration(v.elapsed)} · {v.eta}
        </Text>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e, next) => {
    const b = await read($, bar)
    const snap = await snapshot($)
    const { Box, Text } = $.ui.resolve(e)
    if (snap === null) return <Text dimColor>No task running yet.</Text>

    const { v } = snap
    const cells = barCells(v.frac, Math.max(10, Math.min(40, e.props.bodyColumns - 2)))
    const mark = { completed: '✓', in_progress: '▸', pending: '·' } as const

    return (
      <Box flexDirection="column">
        <Box>
          {cells.map((c, i) => (
            <Text key={`p${i}`} color={c.color} dimColor={c.color === undefined}>
              {c.ch}
            </Text>
          ))}
        </Box>
        <Text color={gradient(v.frac)} bold>
          {Math.round(v.frac * 100)}% · {v.label}
        </Text>
        <Text dimColor>
          {duration(v.elapsed)} · {v.eta}
        </Text>
        {b.items.map(i => (
          <Text key={`t${i.id}`} dimColor={i.status === 'pending'}>
            {mark[i.status]} {i.subject}
          </Text>
        ))}
      </Box>
    )
  })
}
