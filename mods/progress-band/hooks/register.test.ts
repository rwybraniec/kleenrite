import { expect, mock, test } from 'claude-code/testing'

const props = { hasSurvey: false, isWorking: true, maxRows: 3, bodyColumns: 120 }

test('shows a percentage once a prompt is submitted', async ($, on) => {
  mock.clock(on)
  mock.store(on)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('prompt.submit', (_$, e) => ({ text: e.text }))
  await $.prompt.submit({ text: 'go', wait: false, origin: { kind: 'user' } } as never)
  const ui = await $.ui.mount({ plugin: 'progress-band', surface: 'terminal', component: 'AbovePrompt', props: props as never })
  expect(await ui.find({ type: 'Text', text: /%/ })).toBeDefined()
})
