export type MessageLevel = 'info' | 'success' | 'warning' | 'error'

export interface MessageAction {
  label: string
  onSelect: () => void
}

export interface AppMessage {
  id: string
  level: MessageLevel
  title: string
  description: string
  persistent?: boolean
  duration?: number
  action?: MessageAction
}

export const MESSAGE_DURATIONS: Record<Exclude<MessageLevel, 'error'>, number> = {
  info: 4000,
  success: 4000,
  warning: 8000,
}

export const MESSAGE_ICONS: Record<MessageLevel, string> = {
  info: 'i-lucide-info',
  success: 'i-lucide-circle-check',
  warning: 'i-lucide-triangle-alert',
  error: 'i-lucide-circle-alert',
}

export function messageIsPersistent(message: Pick<AppMessage, 'level' | 'persistent'>): boolean {
  return message.persistent ?? message.level === 'error'
}

export function messageDuration(message: Pick<AppMessage, 'level' | 'persistent' | 'duration'>): number {
  if (message.duration !== undefined) return message.duration
  if (messageIsPersistent(message)) return 0
  return MESSAGE_DURATIONS[message.level as Exclude<MessageLevel, 'error'>]
}
