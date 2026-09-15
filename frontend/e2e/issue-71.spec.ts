import { expect, test } from '@playwright/test'

test.describe('Issue #71：SPA 路由焦点与播报', () => {
  test('键盘激活侧栏路由后焦点进入新页面标题', async ({ page }) => {
    await page.goto('/')
    const transactionsLink = page.getByRole('link', { name: '交易', exact: true })
    await transactionsLink.focus()
    await transactionsLink.press('Enter')
    await expect(page).toHaveURL(/\/transactions$/)
    await expect(page.locator('[data-page-title]')).toHaveText('交易')
    await expect(page.locator('[data-page-title]')).toBeFocused()
    await expect(page.locator('[data-page-title]')).toHaveAttribute('tabindex', '-1')

    const announcer = page.locator('[aria-live="polite"]').filter({ hasText: /交易/ })
    await expect(announcer).toHaveCount(1)
  })

  test('query-only 筛选更新不抢走当前控件焦点', async ({ page }) => {
    await page.goto('/transactions')
    const statusFilter = page.getByRole('combobox', { name: '状态筛选' })
    await statusFilter.focus()
    await statusFilter.selectOption('all')
    await expect(page).toHaveURL(/status=all/)
    await expect(statusFilter).toBeFocused()
  })
})
