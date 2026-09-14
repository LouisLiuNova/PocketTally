import { expect, test } from '@playwright/test'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('Issue #61：按钮悬停反馈', () => {
  test('精确指针悬停显示阴影，Reduced Motion 保留状态但取消过渡', async ({ page }) => {
    await page.goto('/')
    const button = page.getByRole('button', { name: '记一笔', exact: true })
    await expect(button).toBeEnabled()
    await expect(button).toHaveClass(/pt-button/)

    await button.hover()
    await expect.poll(() => button.evaluate(element => getComputedStyle(element).boxShadow)).not.toBe('none')

    await page.emulateMedia({ reducedMotion: 'reduce' })
    await expect.poll(() => button.evaluate(element => getComputedStyle(element).transitionDuration)).toBe('0s')
  })

  test('交易列表使用行级 tonal 状态，不把摘要按钮渲染成漂浮卡片', async ({ page }) => {
    await page.goto('/')
    await seedDesktopLedger(page.request)
    await page.goto('/transactions')

    const summaryButton = page.locator('.transaction-summary-button').first()
    await expect(summaryButton).toBeVisible()
    await summaryButton.hover()
    await expect(summaryButton).toHaveCSS('box-shadow', 'none')
    await expect(summaryButton).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)')
    await expect(summaryButton.locator('strong')).not.toHaveCSS('color', 'rgb(0, 92, 175)')
  })
})
