import { expect, test, type Page } from '@playwright/test'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

async function prepareDashboard(page: Page) {
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await seedDesktopLedger(page.request)
  await page.reload()
  await expect(page.locator('.cash-flow-trend--compact')).toBeVisible()
}

test.describe('Issue #92：现金流趋势不阻塞应用壳层', () => {
  test('现金流慢响应期间宽屏侧栏仍可折叠并完成路由切换', async ({ page }) => {
    await prepareDashboard(page)

    let cashFlowStarted = false
    await page.route('**/api/v1/statistics/**', async route => {
      if (!route.request().url().includes('/statistics/cash-flow')) {
        await route.continue()
        return
      }
      cashFlowStarted = true
      await new Promise(resolve => setTimeout(resolve, 1800))
      await route.continue()
    })
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect.poll(() => cashFlowStarted).toBe(true)
    await expect(page.getByRole('status', { name: '正在读取现金流趋势', exact: true })).toBeVisible()

    const sidebar = page.locator('.app-sidebar')
    await page.getByRole('button', { name: '折叠主导航', exact: true }).click()
    await expect(sidebar).toHaveAttribute('data-collapsed', 'true')
    await page.getByRole('link', { name: '交易', exact: true }).click()
    await expect(page).toHaveURL(/\/transactions$/)
    await expect(page.getByRole('heading', { level: 1, name: '交易', exact: true })).toBeVisible()
  })

  test('现金流慢响应期间窄屏抽屉仍可打开并完成路由切换', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await prepareDashboard(page)

    let cashFlowStarted = false
    await page.route('**/api/v1/statistics/**', async route => {
      if (!route.request().url().includes('/statistics/cash-flow')) {
        await route.continue()
        return
      }
      cashFlowStarted = true
      await new Promise(resolve => setTimeout(resolve, 1800))
      await route.continue()
    })
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect.poll(() => cashFlowStarted).toBe(true)
    await expect(page.getByRole('status', { name: '正在读取现金流趋势', exact: true })).toBeVisible()

    const toggle = page.getByRole('button', { name: '打开主导航', exact: true })
    await toggle.click()
    const navigationDialog = page.getByRole('dialog', { name: '主导航' })
    await expect(navigationDialog).toBeVisible()
    await navigationDialog.getByRole('link', { name: '统计分析', exact: true }).click()
    await expect(page).toHaveURL(/\/statistics$/)
    await expect(navigationDialog).toBeHidden()
    await expect(page.getByRole('heading', { level: 1, name: '统计分析', exact: true })).toBeVisible()
  })
})
