import { expect, test } from '@playwright/test'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('Issue #68：Reduced Motion 反馈', () => {
  test('关闭 Nuxt UI 位移/缩放、骨架 pulse，并让图表直接进入终态', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()

    const themeThumb = page.locator('.sidebar-theme-switch-thumb')
    await expect(themeThumb).toBeVisible()
    await expect(themeThumb).toHaveCSS('transition-duration', '0s')

    await seedDesktopLedger(page.request)
    await page.goto('/statistics')
    const chart = page.locator('.cash-flow-chart').first()
    await expect(chart).toBeVisible()
    await expect(chart).toHaveAttribute('data-reduced-motion', 'true')
    await expect(chart).toHaveAttribute('data-chart-duration', '0')

    const tabIndicator = page.locator('.statistics-toolbar__periods [data-slot="indicator"]').first()
    await expect(tabIndicator).toHaveCSS('transition-duration', '0s')

    await page.goto('/transactions')
    await expect(page.getByRole('button', { name: /高级筛选/ })).toBeVisible()
    await page.getByRole('button', { name: /高级筛选/ }).click()
    const collapsibleAnimation = page.locator('.transaction-advanced-filters [class*="collapsible-down"], .transaction-advanced-filters [class*="collapsible-up"]').first()
    await expect(collapsibleAnimation).toHaveCSS('animation-name', 'none')

    await page.goto('/')
    await page.getByRole('button', { name: '记一笔', exact: true }).click()
    const dialog = page.getByRole('dialog').last()
    await expect(dialog).toBeVisible()
    await expect(dialog).toHaveCSS('animation-name', 'none')
  })

  test('加载骨架在 Reduced Motion 下保持静态占位', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/accounts')
    await page.route('**/api/v1/statistics/overview?**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1500))
      await route.continue()
    })
    await page.getByRole('link', { name: '总览', exact: true }).click()
    const skeleton = page.locator('.animate-pulse').first()
    await expect(skeleton).toBeVisible()
    await expect(skeleton).toHaveCSS('animation-name', 'none')
  })
})
