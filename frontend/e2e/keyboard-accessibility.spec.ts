import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Locator, type Page } from '@playwright/test'

async function activate(locator: Locator) {
  await locator.focus()
  await locator.press('Enter')
}

async function typeText(locator: Locator, value: string) {
  await locator.focus()
  await locator.pressSequentially(value)
}

async function saveDialog(page: Page, label: string) {
  await activate(page.getByRole('dialog').getByRole('button', { name: label, exact: true }))
}

test('纯键盘完成核心记账、退款作废、筛选和统计下钻', async ({ page }) => {
  const suffix = Date.now().toString()
  const wallet = '键盘钱包' + suffix
  const category = '键盘餐饮' + suffix
  const adjustment = '键盘调账' + suffix
  const expense = '键盘支出' + suffix
  const refund = '键盘退款' + suffix

  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()

  await activate(page.getByRole('link', { name: '账户', exact: true }))
  const accountTrigger = page.getByRole('button', { name: '新建账户', exact: true })
  await activate(accountTrigger)
  await typeText(page.getByLabel('名称', { exact: true }), wallet)
  await saveDialog(page, '保存')
  await expect(page.getByText(wallet, { exact: true })).toBeVisible()

  await activate(page.getByRole('link', { name: '分类与标签', exact: true }))
  const categoryTrigger = page.getByRole('button', { name: '新建分类', exact: true })
  await activate(categoryTrigger)
  await typeText(page.getByLabel('名称', { exact: true }), category)
  await saveDialog(page, '保存')
  await expect(page.getByText(category, { exact: true })).toBeVisible()

  await activate(page.getByRole('button', { name: '记一笔', exact: true }))
  await page.getByRole('combobox', { name: '交易类型', exact: true }).selectOption('balance_adjustment')
  await page.getByRole('combobox', { name: '账户', exact: true }).selectOption({ label: wallet + ' · ¥0.00' })
  await typeText(page.getByLabel('金额（元）', { exact: true }), '1000')
  await typeText(page.getByLabel('说明', { exact: true }), adjustment)
  await saveDialog(page, '保存交易')
  await expect(page.getByRole('button', { name: '保存交易', exact: true })).toBeHidden()

  await activate(page.getByRole('button', { name: '记一笔', exact: true }))
  await typeText(page.getByLabel('金额（元）', { exact: true }), '80')
  await page.getByRole('combobox', { name: '账户', exact: true }).selectOption({ label: wallet + ' · ¥1,000.00' })
  await page.getByRole('combobox', { name: '分类', exact: true }).selectOption({ label: category })
  await typeText(page.getByLabel('说明', { exact: true }), expense)
  await saveDialog(page, '保存交易')
  await expect(page.getByRole('button', { name: '保存交易', exact: true })).toBeHidden()

  await activate(page.getByRole('link', { name: '交易', exact: true }))
  await typeText(page.getByLabel('搜索交易'), expense)
  const expenseRow = page.getByRole('button').filter({ hasText: expense }).first()
  await expect(expenseRow).toBeVisible()
  await activate(expenseRow)
  await expect(page.getByRole('dialog')).toContainText(expense)

  await activate(page.getByRole('button', { name: '申请退款', exact: true }))
  await typeText(page.getByLabel('金额（元）', { exact: true }), '20')
  await typeText(page.getByLabel('说明', { exact: true }), refund)
  await saveDialog(page, '保存交易')
  await expect(page.getByRole('button', { name: '保存交易', exact: true })).toBeHidden()

  await expect(page.getByRole('button', { name: '申请退款', exact: true })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('button', { name: '申请退款', exact: true })).toBeHidden()
  await page.getByLabel('搜索交易').fill(refund)
  const refundRow = page.getByRole('button').filter({ hasText: refund }).first()
  await expect(refundRow).toBeVisible()
  await activate(refundRow)
  await activate(page.getByRole('button', { name: '作废交易', exact: true }))
  await saveDialog(page, '确认操作')
  await expect(page.getByText('已作废', { exact: true })).toBeVisible()

  await page.waitForTimeout(250)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toBeHidden()
  await page.getByLabel('搜索交易').fill('')
  await page.getByLabel('状态筛选').selectOption('voided')
  await expect(page.getByRole('button').filter({ hasText: refund }).first()).toContainText('已作废')

  await activate(page.getByRole('link', { name: '统计分析', exact: true }))
  const categoryStat = page.locator('.category-stat').filter({ hasText: category }).first()
  await expect(categoryStat).toBeVisible()
  await activate(categoryStat)
  await expect(page.locator('.drill-panel')).toContainText('净支出')
})

test('弹窗焦点约束与恢复、方向键 Tab 和失败重复提交反馈', async ({ page }) => {
  const suffix = Date.now().toString()
  const accountName = '焦点账户' + suffix

  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await activate(page.getByRole('link', { name: '账户', exact: true }))

  const trigger = page.getByRole('button', { name: '新建账户', exact: true })
  await activate(trigger)
  const dialog = page.getByRole('dialog')
  await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest('[role="dialog"]')))).toBe(true)

  for (let index = 0; index < 8; index += 1) {
    await page.keyboard.press('Tab')
    await expect.poll(() => page.evaluate(() => Boolean(document.activeElement?.closest('[role="dialog"]')))).toBe(true)
  }
  await page.keyboard.press('Escape')
  await expect(dialog).toBeHidden()
  await expect(trigger).toBeFocused()

  await activate(trigger)
  await typeText(page.getByLabel('名称', { exact: true }), accountName)
  let writes = 0
  await page.route('**/api/v1/accounts', async route => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    writes += 1
    await new Promise(resolve => setTimeout(resolve, 250))
    await route.abort()
  })
  const save = page.getByRole('dialog').getByRole('button', { name: '保存', exact: true })
  await save.focus()
  await save.press('Enter')
  await save.press('Enter')
  await expect(page.getByRole('alert')).toContainText('无法连接')
  expect(writes).toBe(1)
  await expect(page.getByLabel('名称', { exact: true })).toHaveValue(accountName)
  await expect(save).toBeEnabled()
  await page.unroute('**/api/v1/accounts')
  await page.keyboard.press('Escape')

  await activate(page.getByRole('link', { name: '分类与标签', exact: true }))
  const tabs = page.getByRole('tab')
  await tabs.first().focus()
  await tabs.first().press('ArrowRight')
  await expect(tabs.nth(1)).toBeFocused()
  await expect(tabs.nth(1)).toHaveAttribute('aria-selected', 'true')
  await tabs.nth(1).press('ArrowLeft')
  await expect(tabs.first()).toBeFocused()
  await expect(tabs.first()).toHaveAttribute('aria-selected', 'true')
})

test('关键页面和弹窗没有严重或高优先级自动化无障碍问题', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()

  const pageScan = await new AxeBuilder({ page }).analyze()
  expect(pageScan.violations.filter(item => item.impact === 'critical' || item.impact === 'serious')).toEqual([])

  await activate(page.getByRole('button', { name: '记一笔', exact: true }))
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.waitForTimeout(250)
  const dialogScan = await new AxeBuilder({ page }).include('[role="dialog"]').analyze()
  expect(dialogScan.violations.filter(item => item.impact === 'critical' || item.impact === 'serious')).toEqual([])
})
