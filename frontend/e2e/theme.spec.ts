import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { APPEARANCE_PALETTES, PALETTE_NAMES } from '../app/constants/appearance'

const themes = ['light', 'dark'] as const
const mainRoutes = ['/', '/transactions', '/accounts', '/categories', '/statistics', '/settings'] as const

function colorChannels(value: string) {
  if (value.startsWith('#')) {
    const hex = value.trim().slice(1)
    return hex.length === 3
      ? [...hex].map(item => Number.parseInt(item + item, 16))
      : [0, 2, 4].map(index => Number.parseInt(hex.slice(index, index + 2), 16))
  }
  return [...value.matchAll(/[\d.]+/g)].slice(0, 3).map(match => Number(match[0]))
}

function channel(value: number) {
  const normalized = value / 255
  return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4
}

function luminance(value: string) {
  const channels = colorChannels(value)
  return 0.2126 * channel(channels[0]!) + 0.7152 * channel(channels[1]!) + 0.0722 * channel(channels[2]!)
}

function contrast(first: string, second: string) {
  const [lighter, darker] = [luminance(first), luminance(second)].sort((a, b) => b - a)
  return (lighter + 0.05) / (darker + 0.05)
}

function paletteItem(palette: typeof PALETTE_NAMES[number]) {
  return APPEARANCE_PALETTES.find(candidate => candidate.value === palette)!
}

function paletteRadio(page: Page, palette: typeof PALETTE_NAMES[number]) {
  return page.getByRole('radio', { name: new RegExp(`^${paletteItem(palette).label}`) })
}

async function choosePalette(page: Page, palette: typeof PALETTE_NAMES[number]) {
  const radio = paletteRadio(page, palette)
  await page.locator('.palette-choice').filter({ has: radio }).click()
  await expect(radio).toHaveAttribute('aria-checked', 'true')
}

test('八套配色在亮暗模式下共享完整且可读的语义 token', async ({ page }) => {
  test.setTimeout(180000)
  await page.goto('/settings')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  const themeOption = (label: string) => page.locator('.settings-theme-option').filter({ hasText: label })
  await expect(page.locator('.settings-theme-option').getByRole('radio')).toHaveCount(3)
  await expect(page.locator('.palette-choice').getByRole('radio')).toHaveCount(APPEARANCE_PALETTES.length)

  for (const palette of PALETTE_NAMES) {
    await choosePalette(page, palette)
    for (const theme of themes) {
      await themeOption(theme === 'light' ? '亮色' : '暗色').click()
      await expect(page.locator('html')).toHaveAttribute('data-palette', palette)
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
      await expect(page.locator('html')).toHaveClass(new RegExp(`(^|\\s)${theme}(\\s|$)`))

      const colors = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement)
        const read = (name: string) => style.getPropertyValue(name).trim()
        return {
          primary: read('--ui-primary'), onPrimary: read('--pt-on-primary'),
          container: read('--pt-primary-container'), onContainer: read('--pt-on-primary-container'),
          page: read('--pt-surface-page'), card: read('--pt-surface-card'), muted: read('--pt-surface-muted'),
          elevated: read('--pt-surface-elevated'), accented: read('--pt-surface-accented'),
          text: read('--ui-text'), mutedText: read('--ui-text-muted'), dimmedText: read('--ui-text-dimmed'),
          border: read('--ui-border'), mutedBorder: read('--ui-border-muted'), accentedBorder: read('--ui-border-accented'),
          focus: read('--pt-focus-ring'), success: read('--pt-success'), successContainer: read('--pt-success-container'),
          onSuccessContainer: read('--pt-on-success-container'), warning: read('--pt-warning'), warningContainer: read('--pt-warning-container'),
          onWarningContainer: read('--pt-on-warning-container'), error: read('--pt-error'), errorContainer: read('--pt-error-container'),
          onErrorContainer: read('--pt-on-error-container'), income: read('--pt-chart-income'), expense: read('--pt-chart-expense'),
        }
      })

      expect(Object.values(colors).every(Boolean)).toBe(true)
      expect(contrast(colors.onPrimary, colors.primary), `${palette}/${theme} primary`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.primary, colors.card), `${palette}/${theme} primary on card`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.onContainer, colors.container), `${palette}/${theme} container`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.text, colors.page), `${palette}/${theme} text`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.mutedText, colors.card), `${palette}/${theme} muted text`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.dimmedText, colors.card), `${palette}/${theme} dimmed text`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.border, colors.card), `${palette}/${theme} control border`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.accentedBorder, colors.card), `${palette}/${theme} accented border`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.success, colors.card), `${palette}/${theme} success`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.onSuccessContainer, colors.successContainer), `${palette}/${theme} success container`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.warning, colors.card), `${palette}/${theme} warning`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.onWarningContainer, colors.warningContainer), `${palette}/${theme} warning container`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.error, colors.card), `${palette}/${theme} error`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.onErrorContainer, colors.errorContainer), `${palette}/${theme} error container`).toBeGreaterThanOrEqual(4.5)
      expect(contrast(colors.income, colors.card), `${palette}/${theme} income chart`).toBeGreaterThanOrEqual(3)
      expect(contrast(colors.expense, colors.card), `${palette}/${theme} expense chart`).toBeGreaterThanOrEqual(3)
      for (const [surface, value] of Object.entries({ page: colors.page, card: colors.card, muted: colors.muted, elevated: colors.elevated, accented: colors.accented })) {
        expect(contrast(colors.focus, value), `${palette}/${theme} focus on ${surface}`).toBeGreaterThanOrEqual(3)
      }
      if (theme === 'dark') {
        expect(luminance(colors.page), `${palette} dimmed page floor`).toBeGreaterThanOrEqual(0.015)
        expect(luminance(colors.page)).toBeLessThan(luminance(colors.card))
        expect(luminance(colors.card)).toBeLessThan(luminance(colors.muted))
        expect(luminance(colors.muted)).toBeLessThan(luminance(colors.elevated))
        expect(luminance(colors.elevated)).toBeLessThan(luminance(colors.accented))
      }
      const scan = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
      expect(scan.violations, `${palette}/${theme} axe color contrast`).toEqual([])
    }
  }
})

test('GitHub Appearance 式配色预览使用真实 radio 和候选主题 token', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' })
  await page.goto('/settings')
  const paletteRadios = page.locator('.palette-choice').getByRole('radio')
  await expect(paletteRadios).toHaveCount(8)
  await expect(page.locator('.palette-preview')).toHaveCount(8)

  for (const palette of PALETTE_NAMES) {
    const item = paletteItem(palette)
    await expect(paletteRadio(page, palette)).toHaveAccessibleName(`${item.label} ${item.description}`)
    await expect(page.locator(`[data-palette-preview="${palette}"]`)).toBeVisible()
  }

  const darkPreviewColors = await page.locator('.palette-preview').evaluateAll(elements => elements.map((element) => {
    const style = getComputedStyle(element)
    return { palette: element.getAttribute('data-palette-preview'), page: style.getPropertyValue('--pt-surface-page').trim(), primary: style.getPropertyValue('--pt-primary').trim() }
  }))
  expect(new Set(darkPreviewColors.map(item => item.primary)).size).toBe(8)
  expect(new Set(darkPreviewColors.map(item => item.page)).size).toBe(8)

  await paletteRadio(page, 'ruri').focus()
  await page.keyboard.press('ArrowRight')
  await expect(paletteRadio(page, 'toki')).toHaveAttribute('aria-checked', 'true')
  await paletteRadio(page, 'matsuba').focus()
  await page.keyboard.press('Space')
  await expect(paletteRadio(page, 'matsuba')).toHaveAttribute('aria-checked', 'true')
  await expect(page.locator('.settings-selection-status')).toContainText('松葉色')
  await expect(page.locator('.palette-choice-check')).toHaveCount(1)
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('pockettally-appearance') || '{}').palette)).toBe('matsuba')

  await page.locator('.settings-theme-option').filter({ hasText: '亮色' }).click()
  const lightPreviewPages = await page.locator('.palette-preview').evaluateAll(elements => elements.map(element => getComputedStyle(element).getPropertyValue('--pt-surface-page').trim()))
  expect(lightPreviewPages).not.toEqual(darkPreviewColors.map(item => item.page))
  await expect(page.locator('html')).toHaveAttribute('data-palette', 'matsuba')

  await page.locator('.settings-theme-option').filter({ hasText: '跟随系统' }).click()
  await page.emulateMedia({ colorScheme: 'dark' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  const systemDarkPreviewPages = await page.locator('.palette-preview').evaluateAll(elements => elements.map(element => getComputedStyle(element).getPropertyValue('--pt-surface-page').trim()))
  expect(systemDarkPreviewPages).toEqual(darkPreviewColors.map(item => item.page))
  await page.emulateMedia({ colorScheme: 'light' })
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  const systemLightPreviewPages = await page.locator('.palette-preview').evaluateAll(elements => elements.map(element => getComputedStyle(element).getPropertyValue('--pt-surface-page').trim()))
  expect(systemLightPreviewPages).toEqual(lightPreviewPages)
})

test('八套暗色在六个主页面和目标宽度下保持完整表面', async ({ page }, testInfo) => {
  test.setTimeout(300000)
  const pageErrors: string[] = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.goto('/settings')
  await page.locator('.settings-theme-option').filter({ hasText: '暗色' }).click()

  for (const palette of PALETTE_NAMES) {
    await choosePalette(page, palette)
    for (const route of mainRoutes) {
      await page.goto(route)
      await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
      await expect(page.locator('html')).toHaveAttribute('data-palette', palette)
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
      const surfaces = page.locator('.app-sidebar, .panel, .metric-card, .settings-card, [data-slot="content"]:visible')
      const surfaceCount = await surfaces.count()
      for (let index = 0; index < surfaceCount; index++) {
        const background = await surfaces.nth(index).evaluate(element => getComputedStyle(element).backgroundColor)
        expect(background, `${palette}${route} surface ${index}`).not.toBe('rgb(255, 255, 255)')
        expect(background, `${palette}${route} surface ${index}`).not.toBe('rgb(0, 0, 0)')
      }
      if (testInfo.project.name === 'chromium-1440') {
        const scan = await new AxeBuilder({ page }).withRules(['color-contrast']).analyze()
        expect(scan.violations, `${palette}${route} axe color contrast`).toEqual([])
      }
    }
    await page.goto('/settings')
  }
  expect(pageErrors).toEqual([])
})

test('重点指标使用中性 elevated 表面和小面积品牌强调', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: 'dark', palette: 'ruri' })))
  await page.goto('/')
  const feature = page.locator('.metric-card.feature')
  if (await feature.count()) {
    const colors = await feature.evaluate((element) => {
      const style = getComputedStyle(element)
      const root = getComputedStyle(document.documentElement)
      return { background: style.backgroundColor, elevated: root.getPropertyValue('--pt-surface-elevated').trim(), container: root.getPropertyValue('--pt-primary-container').trim(), shadow: style.boxShadow, primary: root.getPropertyValue('--pt-primary').trim() }
    })
    expect(colors.background).not.toBe(colors.container)
    expect(colors.shadow).toContain('inset')
    expect(colors.shadow).toContain(colorChannels(colors.primary).join(', '))
  }
})

test('新旧偏好可恢复，未知字段独立回退且首屏属性稳定', async ({ page }) => {
  await page.addInitScript(() => {
    if (!localStorage.getItem('pockettally-appearance')) localStorage.setItem('pockettally-appearance', JSON.stringify({ theme: 'dark', palette: 'yamabuki' }))
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
