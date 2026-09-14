import { expect, test } from '@playwright/test'

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
})
