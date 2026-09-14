import { expect, test } from '@playwright/test'

test.describe('Issue #69：侧栏主题模式键盘交互', () => {
  test('主题单选组使用 roving tabindex 和方向键模型', async ({ page }) => {
    await page.goto('/')
    const group = page.getByRole('radiogroup', { name: '主题模式' })
    const radios = group.getByRole('radio')
    await expect(radios).toHaveCount(3)
    await expect(radios.nth(0)).toHaveAttribute('tabindex', '0')
    await expect(radios.nth(1)).toHaveAttribute('tabindex', '-1')
    await expect(radios.nth(2)).toHaveAttribute('tabindex', '-1')

    await radios.nth(0).focus()
    await radios.nth(0).press('ArrowRight')
    await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true')
    await expect(radios.nth(1)).toBeFocused()
    await expect(radios.nth(1)).toHaveAttribute('tabindex', '0')
    await expect(radios.nth(0)).toHaveAttribute('tabindex', '-1')

    await radios.nth(1).press('End')
    await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true')
    await expect(radios.nth(2)).toBeFocused()
    await radios.nth(2).press('Home')
    await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'true')
    await expect(radios.nth(0)).toBeFocused()
  })

  test('Reduced Motion 下选择仍立即同步静态状态', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/')
    const group = page.getByRole('radiogroup', { name: '主题模式' })
    const radios = group.getByRole('radio')
    await radios.nth(0).focus()
    await radios.nth(0).press('ArrowRight')
    await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true')
    await expect(page.locator('.sidebar-theme-switch-thumb')).toHaveCSS('transition-duration', '0s')
  })
})
