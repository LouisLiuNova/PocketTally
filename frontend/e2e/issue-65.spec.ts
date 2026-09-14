import { expect, test } from '@playwright/test'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('Issue #65：精简统计日历', () => {
  test('停止消费趋势请求，日历只显示日期与流入流出', async ({ page }) => {
    const statisticsRequests: string[] = []
    page.on('request', request => {
      if (request.url().includes('/api/v1/statistics/')) statisticsRequests.push(request.url())
    })
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await seedDesktopLedger(page.request)
    await page.goto('/statistics')

    const calendar = page.locator('[data-statistics-section="calendar"]')
    await expect(calendar).toBeVisible()
    await expect(page.locator('[data-statistics-section="expenses"]')).toHaveCount(0)
    expect(statisticsRequests.some(url => url.includes('/statistics/expenses'))).toBe(false)

    const dayButton = calendar.getByRole('button', { name: /净现金流/ }).first()
    await expect(dayButton).toHaveAttribute('aria-label', /退款/)
    await expect(dayButton).toContainText(/(\+|−|无收支)/)
    await expect(dayButton).not.toContainText('净现金流')
    await expect(dayButton).not.toContainText('入 ')
    await expect(dayButton).not.toContainText('出 ')
  })
})
