import { describe, expect, test } from 'bun:test'
import {
  MESSAGE_DURATIONS,
  messageDuration,
  messageIsPersistent,
  type AppMessage,
} from '../app/utils/messages'

const message = (overrides: Partial<AppMessage> = {}): AppMessage => ({
  id: 'test-message',
  level: 'info',
  title: '测试消息',
  description: '用于测试消息策略。',
  ...overrides,
})

describe('全局消息策略', () => {
  test('四种等级均可表达，错误默认持久显示', () => {
    expect(messageIsPersistent(message({ level: 'info' }))).toBe(false)
    expect(messageIsPersistent(message({ level: 'success' }))).toBe(false)
    expect(messageIsPersistent(message({ level: 'warning' }))).toBe(false)
    expect(messageIsPersistent(message({ level: 'error' }))).toBe(true)
    expect(messageIsPersistent(message({ level: 'error', persistent: false }))).toBe(false)
  })

  test('info、success 和 warning 使用固定生命周期，持久消息不自动消失', () => {
    expect(messageDuration(message({ level: 'info' }))).toBe(MESSAGE_DURATIONS.info)
    expect(messageDuration(message({ level: 'success' }))).toBe(MESSAGE_DURATIONS.success)
    expect(messageDuration(message({ level: 'warning' }))).toBe(MESSAGE_DURATIONS.warning)
    expect(messageDuration(message({ level: 'error' }))).toBe(0)
    expect(messageDuration(message({ level: 'warning', persistent: true }))).toBe(0)
    expect(messageDuration(message({ level: 'info', duration: 1200 }))).toBe(1200)
  })
})
