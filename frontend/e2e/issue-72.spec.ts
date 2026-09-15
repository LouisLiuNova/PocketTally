import { expect, test } from '@playwright/test'

test.describe('Issue #72：加载骨架状态播报', () => {
  test('加载期间每个区域只保留具名中文状态，骨架不重复播报', async ({ page }) => {
    await page.route('**/api/v1/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 1200))
      await route.continue()
    })
    await page.goto('/transactions', { waitUntil: 'domcontentloaded' })

    const skeletons = page.locator('.animate-pulse')
    await expect(skeletons.first()).toBeVisible()
    await expect(skeletons).not.toHaveCount(0)
    await expect.poll(() => skeletons.evaluateAll(elements => elements.every(element => element.getAttribute('aria-hidden') === 'true'))).toBe(true)
    await expect(page.locator('[role="alert"][aria-live="polite"][aria-label="loading"]:not([aria-hidden="true"])')).toHaveCount(0)

    const loadingRegions = page.locator('[role="status"][aria-label^="正在"]')
    await expect(loadingRegions.first()).toBeVisible()
  })
})
