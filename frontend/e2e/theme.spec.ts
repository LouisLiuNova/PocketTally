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
  await page.goto('/settings')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  const themeOption = (label: string) => page.locator('.settings-theme-option').filter({ hasText: label })
  const paletteOption = (palette: typeof PALETTE_NAMES[number]) => {
    const item = APPEARANCE_PALETTES.find(candidate => candidate.value === palette)!
    return page.getByRole('button', { name: `选择${item.label}配色，${item.description}`, exact: true })
  }
  await expect(page.locator('.palette-choice')).toHaveCount(APPEARANCE_PALETTES.length)
  await expect(page.locator('.palette-choice-copy strong')).toHaveText(APPEARANCE_PALETTES.map(item => item.label))

  for (const palette of PALETTE_NAMES) {
    await paletteOption(palette).click()
    await expect(paletteOption(palette)).toHaveAttribute('aria-pressed', 'true')
    for (const theme of themes) {
      await themeOption(theme === 'light' ? '亮色' : '暗色').click()
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
  await page.goto('/settings')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await page.locator('.settings-theme-option').filter({ hasText: '跟随系统' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')

  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')

  await page.locator('.settings-theme-option').filter({ hasText: '暗色' }).click()
  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})

test('侧边栏三档主题开关包含系统模式并保持收起态可见', async ({ page }) => {
  await page.goto('/')
  const themeSwitch = page.getByRole('radiogroup', { name: '主题模式', exact: true })
  await expect(themeSwitch).toBeVisible()
  await expect(themeSwitch.getByRole('radio')).toHaveCount(3)
  await expect(themeSwitch.getByRole('radio', { name: '跟随系统', exact: true })).toHaveAttribute('aria-checked', 'true')
  await themeSwitch.getByRole('radio', { name: '暗色', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(themeSwitch.getByRole('radio', { name: '暗色', exact: true })).toHaveAttribute('aria-checked', 'true')
  await expect(page.getByRole('button', { name: '折叠主导航', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '折叠主导航', exact: true }).click()
  await expect(page.getByRole('button', { name: '展开主导航', exact: true })).toBeVisible()
  await expect(themeSwitch).toBeVisible()
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByRole('radiogroup', { name: '主题模式', exact: true }).getByRole('radio', { name: '暗色', exact: true })).toHaveAttribute('aria-checked', 'true')
})
