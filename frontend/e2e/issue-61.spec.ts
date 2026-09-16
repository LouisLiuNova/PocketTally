import { expect, test } from '@playwright/test'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('Issue #61：按钮悬停反馈', () => {
  test('精确指针悬停使用主题 tonal 状态，Reduced Motion 保留状态但取消过渡', async ({ page }) => {
    await page.goto('/')
    const button = page.getByRole('button', { name: '记一笔', exact: true })
    await expect(button).toBeEnabled()
    await expect(button).toHaveClass(/pt-button/)

    const backgroundBeforeHover = await button.evaluate(element => getComputedStyle(element).backgroundColor)
    await button.hover()
    await expect.poll(() => button.evaluate(element => getComputedStyle(element).backgroundColor)).not.toBe(backgroundBeforeHover)
    await expect.poll(() => button.evaluate(element => getComputedStyle(element).boxShadow)).toBe('none')

    await page.emulateMedia({ reducedMotion: 'reduce' })
    await expect.poll(() => button.evaluate(element => getComputedStyle(element).transitionDuration)).toBe('0s')
  })

  test('交易列表摘要按钮使用 tonal 悬停状态，不渲染成漂浮卡片', async ({ page }) => {
    await page.goto('/')
    await seedDesktopLedger(page.request)
    await page.goto('/transactions')

    const summaryButton = page.locator('.transaction-summary-button').first()
    await expect(summaryButton).toBeVisible()
    const backgroundBeforeHover = await summaryButton.evaluate(element => getComputedStyle(element).backgroundColor)
    await summaryButton.hover()
    await expect.poll(() => summaryButton.evaluate(element => getComputedStyle(element).backgroundColor)).not.toBe(backgroundBeforeHover)
    await expect(summaryButton).toHaveCSS('box-shadow', 'none')
    await expect(summaryButton.locator('strong')).not.toHaveCSS('color', 'rgb(0, 92, 175)')
  })

  test('分类树可选择项提供 tonal 悬停状态', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: '分类与标签', exact: true }).click()

    const treeItem = page.getByRole('treeitem').first()
    await expect(treeItem).toBeVisible()
    const backgroundBeforeHover = await treeItem.evaluate(element => getComputedStyle(element).backgroundColor)
    await treeItem.hover()
    await expect.poll(() => treeItem.evaluate(element => getComputedStyle(element).backgroundColor)).not.toBe(backgroundBeforeHover)
  })
})
