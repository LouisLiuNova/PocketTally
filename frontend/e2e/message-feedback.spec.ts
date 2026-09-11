import { expect, test } from '@playwright/test'
import { assertNoHorizontalOverflow } from './helpers/layout'

test('设置页可以手动审阅四级反馈消息', async ({ page }) => {
  await page.goto('/settings')
  await expect(page.getByRole('heading', { name: '消息反馈预览' })).toBeVisible()

  await page.getByRole('button', { name: /^触发信息：/ }).click()
  await expect(page.getByText('信息示例', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: /^触发成功：/ }).click()
  await expect(page.getByText('成功示例', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: /^触发警告：/ }).click()
  await expect(page.getByText('警告示例', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: /^触发错误：/ }).click()
  const alerts = page.locator('[aria-label="需要处理的消息"]')
  await expect(alerts).toContainText('错误示例')
  await expect(alerts.getByRole('button', { name: '再次触发' })).toBeVisible()
  await alerts.getByRole('button', { name: '再次触发' }).click()
  await alerts.getByRole('button', { name: '关闭' }).click()
  await expect(alerts).toBeHidden()

  await page.getByRole('button', { name: '清空预览消息', exact: true }).click()
  await expect(page.getByText('信息示例', { exact: true })).toBeHidden()
  await expect(page.getByText('成功示例', { exact: true })).toBeHidden()
  await expect(page.getByText('警告示例', { exact: true })).toBeHidden()
  await assertNoHorizontalOverflow(page)

  await page.setViewportSize({ width: 390, height: 844 })
  await assertNoHorizontalOverflow(page)
})
