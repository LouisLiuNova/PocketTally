import { expect, test } from '@playwright/test'
import { assertNoHorizontalOverflow, assertNoPageErrors } from './helpers/layout'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('现金流趋势图', () => {
  test('统计页提供图表、完整表格、键盘选择和时间桶下钻', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await seedDesktopLedger(page.request)

    await page.goto('/statistics')
    const trend = page.locator('.cash-flow-trend--full')
    await expect(trend).toBeVisible()
    await expect(trend.locator('.cash-flow-chart')).toBeVisible()
    await expect(page.locator('.cash-flow-summary')).toContainText('退款流入')
    await expect(page.getByRole('button', { name: '查看完整数据表', exact: true })).toBeVisible()

    const chart = trend.locator('.cash-flow-chart')
    await chart.focus()
    await expect(chart).toBeFocused()
    await chart.press('Home')
    await expect(trend.locator('.cash-flow-detail')).toContainText('普通收入')
    await chart.press('End')
    await chart.press('ArrowLeft')
    await expect(trend.locator('.cash-flow-detail')).toContainText('当前时间桶')

    const bars = trend.locator('[data-cash-flow-index] path')
    await expect(bars).not.toHaveCount(0)
    await bars.first().hover()
    await bars.first().click()
    await expect(trend.locator('.cash-flow-detail')).toBeVisible()
    await chart.focus()
    await chart.press('Tab')
    await expect(chart).not.toBeFocused()

    await page.getByRole('button', { name: '查看完整数据表', exact: true }).click()
    const rows = page.locator('.cash-flow-table-scroll tbody tr')
    await expect(rows).not.toHaveCount(0)
    await expect(rows.first().locator('th')).toHaveText(/2026-/)
    await chart.focus()
    await chart.press('Enter')
    await expect(page).toHaveURL(/\/transactions\?.*start=.*end=/)
    await assertNoPageErrors(page, errors)
  })

  test('总览使用 compact，不重复汇总或产生页面横向溢出', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await seedDesktopLedger(page.request)
    await page.reload()

    const trend = page.locator('.cash-flow-trend--compact')
    await expect(trend).toBeVisible()
    await expect(trend.locator('.cash-flow-chart')).toBeVisible()
    await expect(page.locator('.overview-flow .cash-flow-summary')).toHaveCount(0)
    await expect(trend.locator('.cash-flow-table-wrap')).toHaveCount(0)
    await assertNoHorizontalOverflow(page)

    await page.setViewportSize({ width: 390, height: 844 })
    await expect(trend).toBeVisible()
    await assertNoHorizontalOverflow(page)
    await assertNoPageErrors(page, errors)
  })
})
