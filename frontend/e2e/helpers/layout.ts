import { expect, type Locator, type Page } from '@playwright/test'

export async function assertNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow, `页面在 ${page.viewportSize()?.width}px 视口出现横向溢出`).toBe(false)
}

export async function assertWithinViewport(locator: Locator, label: string) {
  await expect(locator, `${label} 应可见`).toBeVisible()
  const box = await locator.boundingBox()
  const viewport = locator.page().viewportSize()
  expect(box, `${label} 应有可测量尺寸`).not.toBeNull()
  expect(viewport).not.toBeNull()
  if (!box || !viewport) return
  expect(box.x, `${label} 左侧不能超出视口`).toBeGreaterThanOrEqual(0)
  expect(box.y, `${label} 顶部不能超出视口`).toBeGreaterThanOrEqual(0)
  expect(box.x + box.width, `${label} 右侧不能超出视口`).toBeLessThanOrEqual(viewport.width)
  expect(box.y + box.height, `${label} 底部不能超出视口`).toBeLessThanOrEqual(viewport.height)
}

export async function assertDialogWithinViewport(page: Page) {
  const dialog = page.getByRole('dialog').last()
  await assertWithinViewport(dialog, '弹窗')
}

export async function assertNoPageErrors(page: Page, errors: string[]) {
  expect(errors, '页面不应产生未处理的 JavaScript 错误').toEqual([])
}
