import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { assertNoHorizontalOverflow } from './helpers/layout'

test('宽屏壳层支持路由导航、折叠状态与状态提示', async ({ page }) => {
  await page.goto('/transactions')
  await expect(page.getByRole('heading', { level: 1, name: '交易', exact: true })).toBeVisible()
  await expect(page.getByRole('navigation', { name: 'breadcrumb' })).toContainText('总览')
  await expect(page.getByRole('navigation', { name: 'breadcrumb' })).toContainText('交易')
  await expect(page.getByRole('link', { name: '交易', exact: true })).toHaveAttribute('aria-current', 'page')

  const sidebar = page.locator('.app-sidebar')
  await expect(sidebar).toHaveAttribute('data-collapsed', 'false')
  await page.getByRole('button', { name: '折叠主导航', exact: true }).click()
  await expect(sidebar).toHaveAttribute('data-collapsed', 'true')
  await expect(page.getByRole('link', { name: '交易', exact: true })).toBeVisible()

  const currencyStatus = page.getByLabel('货币：CNY', { exact: true })
  await currencyStatus.hover()
  await expect(page.locator('[data-slot="content"]').filter({ hasText: '货币：CNY' })).toBeVisible()
  await page.getByLabel('个人账本', { exact: true }).focus()
  await page.keyboard.press('Tab')
  await expect(currencyStatus).toBeFocused()
  await expect(page.locator('.ledger-status-item [data-slot="label"]')).toHaveCount(0)

  await page.getByRole('button', { name: '展开主导航', exact: true }).click()
  await expect(sidebar).toHaveAttribute('data-collapsed', 'false')
  await assertNoHorizontalOverflow(page)
})

test('窄屏使用可访问滑出导航并在路由切换后关闭', async ({ page }) => {
  await page.setViewportSize({ width: 680, height: 800 })
  await page.goto('/')
  await expect(page.locator('.app-sidebar')).toBeHidden()

  const toggle = page.getByRole('button', { name: '打开主导航', exact: true })
  await expect(toggle).toBeVisible()
  await toggle.click()

  const navigationDialog = page.getByRole('dialog', { name: '主导航' })
  await expect(navigationDialog).toBeVisible()
  await navigationDialog.getByRole('link', { name: '统计分析', exact: true }).click()
  await expect(page).toHaveURL('/statistics')
  await expect(navigationDialog).toBeHidden()
  await expect(page.getByRole('heading', { level: 1, name: '统计分析', exact: true })).toBeVisible()
  await assertNoHorizontalOverflow(page)

  await toggle.click()
  await expect(navigationDialog).toBeVisible()
  const scan = await new AxeBuilder({ page }).analyze()
  expect(scan.violations.filter(item => item.impact === 'critical' || item.impact === 'serious')).toEqual([])
})
