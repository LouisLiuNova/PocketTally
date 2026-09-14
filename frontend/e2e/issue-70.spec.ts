import { expect, test } from '@playwright/test'

test.describe('Issue #70：侧栏只读状态项语义', () => {
  test('账本、货币和统计边界不再暴露为无动作按钮', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()

    for (const label of ['个人账本', '货币：CNY', '统计边界：Asia/Shanghai']) {
      await expect(page.getByRole('button', { name: label, exact: true })).toHaveCount(0)
      await expect(page.locator(`[aria-label="${label}"]`).first()).toBeVisible()
    }

    const tabbableLabels = await page.locator('.ledger-status-item').evaluateAll(elements => elements.map(element => ({
      tabIndex: (element as HTMLElement).tabIndex,
      tagName: element.tagName,
    })))
    expect(tabbableLabels).toHaveLength(3)
    expect(tabbableLabels.every(item => item.tabIndex < 0 && item.tagName !== 'BUTTON')).toBe(true)
  })
})
