import { expect, test } from '@playwright/test'
import { assertDialogWithinViewport, assertNoHorizontalOverflow, assertNoPageErrors } from './helpers/layout'
import { seedDesktopLedger } from './helpers/ledger-fixtures'

test.describe('Chromium 桌面兼容性矩阵', () => {
  test('空账本和六个主页面无布局阻断', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    const accounts = await page.request.get('http://127.0.0.1:8012/api/v1/accounts')
    const accountItems = (await accounts.json()) as unknown[]
    if (accountItems.length === 0) {
      await expect(page.getByText('欢迎来到你的账本')).toBeVisible()
    }

    for (const label of ['总览', '交易', '账户', '分类与标签', '统计分析', '设置']) {
      await page.getByRole('link', { name: label, exact: true }).click()
      await assertNoHorizontalOverflow(page)
      await expect(page.locator('main')).toBeVisible()
      if (label === '统计分析') {
        const metrics = page.locator('.statistics-metrics')
        await expect(metrics).toBeVisible()
        await expect(metrics).toHaveCSS('gap', '20px')
        await expect(metrics).toHaveCSS('margin-bottom', '20px')
      }
    }

    await page.getByRole('link', { name: '设置', exact: true }).click()
    await page.locator('.settings-theme-option').filter({ hasText: '亮色' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
    await page.locator('.settings-theme-option').filter({ hasText: '暗色' }).click()
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
    await assertNoHorizontalOverflow(page)
    await assertNoPageErrors(page, errors)
  })

  test('常规数据、长文本、分页、统计和弹窗保持可用', async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    const fixture = await seedDesktopLedger(page.request)

    await page.reload()
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await assertNoHorizontalOverflow(page)

    await page.getByRole('link', { name: '交易', exact: true }).click()
    await expect(page.getByText(/服务端共 \d+ 笔/)).toBeVisible()
    await expect(page.getByRole('button', { name: '下一页', exact: true })).toBeVisible()
    await page.getByRole('button', { name: '下一页', exact: true }).click()
    await expect(page.getByText(/^[2-9] \/ [2-9]$/)).toBeVisible()
    await assertNoHorizontalOverflow(page)

    await page.getByLabel('搜索交易').fill(`可打开详情-${fixture.suffix}`)
    await page.getByRole('button').filter({ hasText: `可打开详情-${fixture.suffix}` }).click()
    await assertDialogWithinViewport(page)
    await page.getByRole('button', { name: '编辑交易', exact: true }).click()
    await assertDialogWithinViewport(page)
    await page.getByRole('button', { name: '关闭', exact: true }).click()

    await page.getByRole('button', { name: '申请退款', exact: true }).click()
    await assertDialogWithinViewport(page)
    await page.getByRole('button', { name: '关闭', exact: true }).click()
    await page.getByRole('button', { name: '作废交易', exact: true }).click()
    await assertDialogWithinViewport(page)
    await page.getByRole('button', { name: '取消', exact: true }).click()
    await page.keyboard.press('Escape')

    await page.getByRole('link', { name: '账户', exact: true }).click()
    const walletCard = page.locator('.balance-card').filter({ hasText: fixture.wallet.name })
    await walletCard.getByRole('button', { name: '流水', exact: true }).click()
    await expect.poll(() => new URL(page.url()).searchParams.get('accountId')).toBe(fixture.wallet.id)
    await page.goBack()
    await expect(page).toHaveURL(/\/accounts$/)
    await walletCard.getByRole('button', { name: '删除', exact: true }).click()
    await assertDialogWithinViewport(page)
    await page.getByRole('button', { name: '取消', exact: true }).click()
    await page.getByRole('button', { name: '新建账户', exact: true }).click()
    await assertDialogWithinViewport(page)
    const failedName = `保存失败后仍保留-${fixture.suffix}`
    await page.getByLabel('名称', { exact: true }).fill(failedName)
    await page.route('**/api/v1/accounts', route => route.abort())
    await page.getByRole('button', { name: '保存', exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(page.getByLabel('名称', { exact: true })).toHaveValue(failedName)
    await page.unroute('**/api/v1/accounts')
    await page.getByRole('button', { name: '关闭', exact: true }).click()

    await page.getByRole('link', { name: '分类与标签', exact: true }).click()
    await expect(page.getByText(fixture.longName, { exact: true })).toBeVisible()
    await assertNoHorizontalOverflow(page)

    await page.getByRole('link', { name: '统计分析', exact: true }).click()
    await page.getByRole('button', { name: '近 12 个月', exact: true }).click()
    await expect.poll(() => new URL(page.url()).searchParams.get('preset')).toBe('twelve_months')
    await page.getByLabel('粒度').selectOption('month')
    await expect.poll(() => new URL(page.url()).searchParams.get('granularity')).toBe('month')
    await expect(page.getByText('现金流趋势', { exact: true })).toBeVisible()
    await assertNoHorizontalOverflow(page)

    await page.locator('.bucket-button').first().click()
    await expect(page).toHaveURL(/\/transactions\?.*start=.*end=/)
    await page.goBack()
    await expect(page.getByLabel('粒度')).toHaveValue('month')

    await page.locator('.calendar-grid button').first().click()
    await expect.poll(() => new URL(page.url()).pathname).toBe('/transactions')
    expect(new URL(page.url()).searchParams.get('start')).toBeNull()
    expect(new URL(page.url()).searchParams.get('end')).toMatch(/^\d{4}-\d{2}-02$/)
    await page.goBack()
    await expect(page.getByRole('button', { name: '近 12 个月', exact: true })).toHaveClass(/active/)

    await page.locator('.category-stat').first().click()
    await expect(page.locator('.drill-panel')).toBeVisible()
    await assertNoHorizontalOverflow(page)
    await assertNoPageErrors(page, errors)
  })
})
