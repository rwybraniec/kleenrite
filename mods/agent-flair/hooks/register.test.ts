import { expect, test } from 'claude-code/testing'

import { register } from './register'

const toolUse = (subagent_type: string) => ({
  tool_use_id: 't1',
  tool: 'Agent',
  input: { subagent_type, description: 'look around', name: 'scout-1' },
  isRunning: true,
  isErrored: false,
  isInterrupted: false,
})

for (const [type, title] of [
  ['Explore', 'SCOUT'],
  ['Plan', 'ARCHITECT'],
  ['cockroachdb:cockroachdb-dba', 'DB-WARDEN'],
  ['mystery', 'AGENT'],
] as const) {
  test(`${type} draws as ${title}`, async ($, on) => {
    register(on, {})
    const ui = await $.ui.mount({
      plugin: 'agent-flair',
      surface: 'terminal',
      component: 'ToolUse',
      props: toolUse(type),
    })
    expect(await ui.find({ type: 'Text', text: new RegExp(title) })).toBeDefined()
  })
}
