import { expect, test } from '@playwright/test'

test.describe('Issue #22：单所有者登录边界', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('匿名访问账本页面会进入登录页并保留回跳地址', async ({ page }) => {
    await page.goto('/accounts')
    await expect(page).toHaveURL(/\/login\?redirect=/)
    await expect(page.getByRole('heading', { name: '登录个人账本', exact: true })).toBeVisible()
    await expect(page.getByRole('textbox', { name: '用户名', exact: true })).toBeVisible()
  })

  test('错误凭据显示通用错误，正确凭据完成会话建立', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('textbox', { name: '用户名', exact: true }).fill('e2e-owner')
    await page.getByRole('textbox', { name: '密码', exact: true }).fill('wrong-password-that-is-long')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('用户名或密码错误')

    await page.getByRole('textbox', { name: '密码', exact: true }).fill('PocketTally-E2E-Password-2026!')
    await page.getByRole('button', { name: '登录', exact: true }).click()
    await expect(page).toHaveURL(/\/$/)
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  })
})
