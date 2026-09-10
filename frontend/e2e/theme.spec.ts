import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { APPEARANCE_PALETTES, PALETTE_NAMES } from '../app/constants/appearance'

const themes = ['light', 'dark'] as const

function channel(value: number) {
  const normalized = value / 255
  return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4
}

function luminance(value: string) {
  const hex = value.trim().replace('#', '')
  const channels = hex.length === 3
    ? [...hex].map(item => Number.parseInt(item + item, 16))
    : [0, 2, 4].map(index => Number.parseInt(hex.slice(index, index + 2), 16))
  return 0.2126 * channel(channels[0]!) + 0.7152 * channel(channels[1]!) + 0.0722 * channel(channels[2]!)
}

function contrast(first: string, second: string) {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a)
  return (lighter + 0.05) / (darker + 0.05)
}

test('八套配色在亮暗模式下共享完整且可读的语义 token', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '外观设置', exact: true }).click()
  const themeSelect = page.getByLabel('主题')
  const paletteSelect = page.getByLabel('配色')
  await expect(paletteSelect.locator('option')).toHaveCount(8)
  expect(await paletteSelect.locator('option').allTextContents()).toEqual(APPEARANCE_PALETTES.map(item => item.label))

  for (const palette of PALETTE_NAMES) {
    await paletteSelect.selectOption(palette)
    for (const theme of themes) {
      await themeSelect.selectOption(theme)
      await expect(page.locator('html')).toHaveAttribute('data-palette', palette)
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      await expect(page.locator('html')).toHaveClass(new RegExp(`(^|\\s)${theme}(\\s|$)`))

      const colors = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement)
        const read = (name: string) => style.getPropertyValue(name).trim()
        return {
          primary: read('--ui-primary'),
          onPrimary: read('--pt-on-primary'),
          container: read('--pt-primary-container'),
          onContainer: read('--pt-on-primary-container'),
          page: read('--pt-surface-page'),
          card: read('--pt-surface-card'),
          text: read('--ui-text'),
          mutedText: read('--ui-text-muted'),
          border: read('--ui-border'),
          focus: read('--pt-focus-ring'),
          income: read('--pt-chart-income'),
          expense: read('--pt-chart-expense'),
        }
      })

      expect(Object.values(colors).every(Boolean)).toBe(true)
      expect(contrast(colors.onPrimary, colors.primary), `${palette}/${theme} primary`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.onContainer, colors.container), `${palette}/${theme} container`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.text, colors.page), `${palette}/${theme} text`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.mutedText, colors.page), `${palette}/${theme} muted text`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.border, colors.card), `${palette}/${theme} border`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.focus, colors.page), `${palette}/${theme} focus`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.income, colors.card), `${palette}/${theme} income chart`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.expense, colors.card), `${palette}/${theme} expense chart`).toBeGreaterThanOrEqual(3)
      const scan = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(scan.violations, `${palette}/${theme} axe color contrast`).toEqual([])
    }
  }
})

test('新旧偏好可恢复，未知字段独立回退且首屏属性稳定', async ({ page }) => {
  await page.addInitScript(() => {
    if (!localStorage.getItem('pockettally-appearance')) {
      localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: 'dark', palette: 'yamabuki' }))
    }
  })
  await page.goto('/', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'yamabuki')
  await expect(page.locator('html')).toHaveClass(/dark/)
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'yamabuki')

  await page.evaluate(() => {
    localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: 'dark', palette: 'unknown' }))
    localStorage.removeItem('pockettally-color-mode')
  })
  await page.reload({ waitUntil: 'domcontentloaded' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'ruri')
})

test('跟随系统实时切换，显式主题不受系统变化影响', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '外观设置', exact: true }).click()
  await page.getByLabel('主题').selectOption('system')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')

  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')

  await page.getByLabel('主题').selectOption('dark')
  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})
