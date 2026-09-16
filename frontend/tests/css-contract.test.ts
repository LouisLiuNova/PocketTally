import { readFileSync } from 'node:fs'
import { describe, expect, test } from 'bun:test'

const cssFiles = [
  'app/assets/css/main.css',
  'app/assets/css/mvp.css',
  'app/assets/css/theme.css',
  'app/assets/css/layout.css',
  'app/assets/css/resource-editor.css',
]

const legacySelectors = [
  'metric-card',
  'composer',
  'mvp-transaction',
  'resource-row',
  'detail-drawer',
  'modal-backdrop',
  'category-picker',
  'subcategory-popover',
  'calculator-popover',
  'cash-calendar',
  'calendar-panel',
  'segmented',
  'period-tabs',
  'filter-chip',
  'ledger-row',
  'workspace-view',
  'view-toolbar',
  'topbar',
  'nav-item',
  'donut',
  'sparkline',
  'chart-wrap',
  'account-list',
]

function readCss() {
  return cssFiles.map(file => readFileSync(file, 'utf8')).join('\n')
}

describe('Issue #37：遗留通用 CSS 契约', () => {
  test('不再保留早期原型的通用组件选择器', () => {
    const css = readCss()

    for (const selector of legacySelectors) {
      const pattern = new RegExp(`(?:^|[,{]\\s*)\\.${selector}(?![\\w-])`)
      expect(css).not.toMatch(pattern)
    }
  })

  test('通用 UI 依赖仍由 Nuxt UI 提供', () => {
    const nuxtConfig = readFileSync('nuxt.config.ts', 'utf8')
    const appConfig = readFileSync('app/app.config.ts', 'utf8')
    const packageJson = readFileSync('package.json', 'utf8')

    expect(nuxtConfig).toContain("modules: ['@nuxt/ui']")
    expect(appConfig).toContain("base: 'pt-button'")
    expect(packageJson).not.toMatch(/shadcn/i)
  })
})
