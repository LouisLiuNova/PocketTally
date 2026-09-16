import { expect, test } from '@playwright/test'
import { assertNoHorizontalOverflow, assertNoPageErrors } from './helpers/layout'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

const routes = ['/', '/transactions', '/accounts', '/categories', '/statistics', '/settings'] as const

async function assertReadableTypography(page: import('@playwright/test').Page) {
  const result = await page.evaluate(() => {
    const root = getComputedStyle(document.documentElement)
    const samples: Array<{ text: string; size: number; selector: string }> = []
    for (const element of document.querySelectorAll<HTMLElement>('body *')) {
      if (!element.innerText?.trim()) continue
      const style = getComputedStyle(element)
      if (style.display === 'none' || style.visibility === 'hidden') continue
      if (element.closest('[aria-hidden="true"]')) continue
      if (element.closest('.cash-flow-chart, .palette-preview')) continue
      const size = Number.parseFloat(style.fontSize)
      if (size < 12) {
        const className = typeof element.className === 'string' && element.className ? `.${element.className.trim().replace(/\s+/g, '.')}` : ''
        samples.push({ text: element.innerText.trim().slice(0, 40), size, selector: `${element.tagName.toLowerCase()}${className}` })
      }
    }
    return {
      fontFamily: getComputedStyle(document.body).fontFamily,
      bodyLineHeight: getComputedStyle(document.body).lineHeight,
      textSm: root.getPropertyValue('--text-sm').trim(),
      textSmLineHeight: root.getPropertyValue('--text-sm--line-height').trim(),
      samples,
    }
  })

  expect(result.fontFamily).not.toContain('Inter')
  expect(result.textSm).toMatch(/^0?\.875rem$/)
  expect(result.textSmLineHeight).toBe('1.5714')
  expect(result.samples, `发现未登记的 12px 以下可读文字：${JSON.stringify(result.samples)}`).toEqual([])
}

test.describe('Issue #67：排版契约与窄屏可用性', () => {
  test('六个页面在 320px 下不产生页面溢出且保持排版可读', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    const fixture = await seedDesktopLedger(page.request)
    await page.setViewportSize({ width: 320, height: 900 })

    for (const route of routes) {
      await page.goto(route)
      await expect(page.locator('[data-page-title]')).toBeVisible()
      await assertNoHorizontalOverflow(page)
      await assertReadableTypography(page)
      if (route === '/categories') await expect(page.getByText(fixture.longName, { exact: true })).toBeVisible()
    }

    await assertNoPageErrors(page, errors)
  })

  test('320px 日历仅在日历区域横向滚动，键盘仍可打开日期流水', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await seedDesktopLedger(page.request)
    await page.setViewportSize({ width: 320, height: 900 })
    await page.goto('/statistics')

    const calendar = page.locator('.calendar-scroll')
    await expect(calendar).toBeVisible()
    const dimensions = await calendar.evaluate(element => ({ clientWidth: element.clientWidth, scrollWidth: element.scrollWidth }))
    expect(dimensions.scrollWidth, '七列日历应在自己的容器内保留可滚动宽度').toBeGreaterThan(dimensions.clientWidth)
    await assertNoHorizontalOverflow(page)

    const day = calendar.locator('button').first()
    await day.focus()
    await expect(day).toBeFocused()
    await day.press('Enter')
    await expect(page).toHaveURL(/\/transactions\?(?=.*start=)(?=.*end=)/)
  })

  test('注入 WCAG 1.4.12 排版覆盖后，交易筛选与操作仍可用', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await seedDesktopLedger(page.request)
    await page.goto('/transactions')
    await page.addStyleTag({
      content: `
        body * { line-height: 1.5 !important; letter-spacing: .12em !important; word-spacing: .16em !important; }
        p { margin-bottom: 2em !important; }
      `,
    })
    await assertNoHorizontalOverflow(page)
    await expect(page.getByRole('button', { name: /高级筛选/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeVisible()

    await page.evaluate(() => { document.documentElement.style.zoom = '2' })
    await expect(page.getByRole('button', { name: /高级筛选/ })).toBeVisible()
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeVisible()
  })
})
