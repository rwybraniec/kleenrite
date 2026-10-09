export type AgentFlairFrame = number

declare module 'claude-code' {
  interface PluginState {
    'agent-flair': { frame: AgentFlairFrame }
  }
}
