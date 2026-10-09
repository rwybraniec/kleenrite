export type BandItem = { id: string; subject: string; status: 'pending' | 'in_progress' | 'completed' }

export type Bar = {
  items: BandItem[]
  planStart: number | null
  startedAt: number | null
  endedAt: number | null
  tick: number
}

declare module 'claude-code' {
  interface PluginState {
    'progress-band': { bar: Bar }
  }
}
