import { expect, test, type Page } from '@playwright/test'
import { assertNoHorizontalOverflow } from './helpers/layout'

const header = '交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注'
function bill(suffix: string) {
  return Buffer.from(`${header}\n2026-07-03 12:34:56,餐饮美食,测试商户,,${'长说明'.repeat(25)},支出,12.34,测试卡(1234),交易成功,IMPORT-${suffix},,\n2026-07-03 12:35:00,退款,测试商户,,退款,不计收支,2.00,测试卡(1234),退款成功,REFUND-${suffix},,\n`)
}
async function hydrated(page: Page) {
  await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
}
async function select(page: Page, label: string, value: string) {
  await page.getByLabel(label, { exact: true }).click()
  await page.getByRole('option', { name: value, exact: true }).click()
}
async function upload(page: Page, suffix: string) {
  await page.goto('/imports'); await hydrated(page)
  await page.locator('input[type=file]').setInputFiles({ name: '个人账单.csv', mimeType: 'text/csv', buffer: bill(suffix) })
  await page.getByRole('button', { name: '解析账单', exact: true }).click()
  await expect(page.getByText('草稿已保存', { exact: false })).toBeVisible()
  await expect(page.locator('input[type=file]')).toBeEnabled()
}

test('导入：上传、批量修正、刷新恢复、回滚重试、完成跳转与去重', async ({ page, request }, testInfo) => {
  const suffix = `${testInfo.project.name}-${Date.now()}`
  const response = await request.post('http://127.0.0.1:8012/api/v1/accounts', { data: { name: `导入账户-${suffix}`, type: 'debit' } })
  expect(response.ok()).toBe(true)
  const account = await response.json()
  const categories = await (await request.get('http://127.0.0.1:8012/api/v1/categories')).json()
  const category = categories.find((c: any) => c.purpose === 'expense')
  await upload(page, suffix)
  await expect(page.getByRole('button', { name: '确认导入', exact: true })).toBeDisabled()
  await select(page, '来源支付方式', '测试卡(1234)')
  await select(page, '映射账户', account.name)
  await select(page, '批量分类', category.name)
  await page.getByRole('button', { name: '应用到该支付方式', exact: true }).click()
  await expect(page.getByRole('button', { name: '确认导入', exact: true })).toBeEnabled()
  const batchUrl = page.url()
  await page.reload(); await hydrated(page)
  await expect(page.getByRole('button', { name: '确认导入', exact: true })).toBeEnabled()
  const trigger = page.getByRole('button', { name: /查看第 .* 行并修正/ }).first()
  await trigger.focus(); await trigger.press('Enter')
  const editor = page.getByRole('dialog', { name: '修正候选记录', exact: true })
  await expect(editor.getByLabel('发生时间（上海）')).toHaveValue('2026-07-03T12:34:56')
  await editor.getByLabel('说明', { exact: true }).fill(`修正后的说明-${suffix}`)
  await editor.getByRole('button', { name: '保存修正', exact: true }).click()
  await expect(editor).toBeHidden(); await expect(trigger).toBeFocused()
  await assertNoHorizontalOverflow(page)
  await page.screenshot({ path: testInfo.outputPath('imports-preview.png') })
  await page.getByRole('button', { name: '确认导入', exact: true }).click()
  const confirmation = page.getByRole('dialog', { name: '确认整批导入', exact: true })
  await confirmation.getByRole('button', { name: '提交整批', exact: true }).click()
  await expect(confirmation.getByText('借记账户余额不足', { exact: false })).toBeVisible()
  await confirmation.getByRole('button', { name: '取消', exact: true }).click()
  await expect(page.getByText(`修正后的说明-${suffix}`, { exact: true })).toBeVisible()
  const adjustment = await request.post('http://127.0.0.1:8012/api/v1/transactions', { data: { type: 'balance_adjustment', sourceAccountId: account.id, amount: 100, balanceAdjustmentDirection: 'increase', occurredAt: '2026-01-01T00:00:00Z' } })
  expect(adjustment.ok()).toBe(true)
  await page.getByRole('button', { name: '确认导入', exact: true }).click()
  await confirmation.getByRole('button', { name: '提交整批', exact: true }).click()
  await expect(page.getByText('导入已完成', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: '查看导入期间交易', exact: true }).click()
  await expect(page).toHaveURL(/\/transactions\?.*start=2026-07-03/)
  await page.goto(batchUrl); await hydrated(page)
  await page.locator('input[type=file]').setInputFiles({ name: '重复账单.csv', mimeType: 'text/csv', buffer: bill(suffix) })
  await page.getByRole('button', { name: '解析账单', exact: true }).click()
  await expect(page.getByText('来源单号已入账', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '确认导入', exact: true })).toBeDisabled()
})

test('导入：失败保留修正、状态筛选、退款来源与草稿删除', async ({ page }) => {
  await upload(page, String(Date.now()))
  let failPatch = true
  await page.route('**/api/v1/imports/*', async route => {
    if (route.request().method() === 'PATCH' && failPatch) { failPatch = false; await route.fulfill({ status: 500, json: { message: '修正暂时无法保存' } }) }
    else await route.continue()
  })
  await page.getByRole('button', { name: /查看第 .* 行并修正/ }).first().click()
  const editor = page.getByRole('dialog', { name: '修正候选记录', exact: true })
  await editor.getByLabel('说明', { exact: true }).fill('失败后保留的内容')
  await editor.getByRole('button', { name: '保存修正', exact: true }).click()
  await expect(editor.getByText('修正暂时无法保存', { exact: true })).toBeVisible()
  await expect(editor.getByLabel('说明', { exact: true })).toHaveValue('失败后保留的内容')
  await editor.getByRole('button', { name: '保存修正', exact: true }).click()
  await expect(editor).toBeHidden()
  await select(page, '筛选导入状态', '退款待处理')
  await expect(page.getByRole('button', { name: /查看第 .* 行来源/ })).toHaveCount(1)
  await page.getByRole('button', { name: /查看第 .* 行来源/ }).click()
  const source = page.getByRole('dialog', { name: '来源详情', exact: true })
  await expect(source.getByText('退款成功', { exact: true })).toBeVisible()
  await expect(source.getByRole('button', { name: '保存修正' })).toHaveCount(0)
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: '删除草稿', exact: true }).click()
  await page.getByRole('dialog', { name: '删除未提交草稿' }).getByRole('button', { name: '删除草稿', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeHidden()
  await expect(page).toHaveURL(/\/imports$/)
})

test('导入：读取重试和异步旧批次不能覆盖当前选择', async ({ page }) => {
  await upload(page, `old-${Date.now()}`)
  const oldUrl = page.url()
  const oldId = new URL(oldUrl).searchParams.get('batchId')!
  const newName = `新批次-${Date.now()}.csv`
  await page.locator('input[type=file]').setInputFiles({ name: newName, mimeType: 'text/csv', buffer: bill(`new-${Date.now()}`) })
  await page.getByRole('button', { name: '解析账单', exact: true }).click()
  await expect(page.getByRole('heading', { name: newName, exact: true })).toBeVisible()
  await expect(page).not.toHaveURL(oldUrl)
  await expect(page.locator('input[type=file]')).toBeEnabled()
  const newUrl = page.url()
  await page.goto(oldUrl); await hydrated(page)
  await expect(page.getByRole('heading', { name: '个人账单.csv', exact: true })).toBeVisible()
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let held = false
  await page.route('**/api/v1/imports/*?**', async route => {
    if (route.request().url().includes(oldId) && route.request().url().includes('status=needs_account')) { held = true; await gate }
    await route.continue()
  })
  await select(page, '筛选导入状态', '待补账户')
  await expect.poll(() => held).toBe(true)
  await select(page, '选择导入批次', `${newName} · 草稿`)
  await expect(page).toHaveURL(newUrl)
  await expect(page.getByRole('heading', { name: newName, exact: true })).toBeVisible()
  const stale = page.waitForResponse(response => response.url().includes(oldId) && response.url().includes('status=needs_account'))
  release(); await stale
  await expect(page.getByRole('heading', { name: newName, exact: true })).toBeVisible()
  await page.unroute('**/api/v1/imports/*?**')
  let fail = true
  await page.route('**/api/v1/imports/*?**', async route => {
    if (fail) { await route.fulfill({ status: 500, json: { message: '草稿读取失败' } }) }
    else await route.continue()
  })
  await page.getByRole('button', { name: '重新读取', exact: true }).click()
  await expect(page.getByText('草稿读取失败', { exact: true })).toBeVisible()
  fail = false
  await page.getByRole('button', { name: '重新读取', exact: true }).click()
  await expect(page.getByText('草稿读取失败', { exact: true })).toBeHidden()
})

test('真实微信 XLSX：浏览器上传及所有来源行核对', async ({ page }) => {
  const root = process.env.POCKET_TALLY_REAL_BILLS_DIR
  test.skip(!root, '真实文件只在用户本地验收')
  const { readdir } = await import('node:fs/promises')
  const filename = (await readdir(root!)).find(name => name.startsWith('微信') && name.endsWith('.xlsx'))!
  expect(filename).toBeTruthy()
  await page.goto('/imports'); await hydrated(page)
  await page.locator('input[type=file]').setInputFiles(`${root}/${filename}`)
  await page.getByRole('button', { name: '解析账单', exact: true }).click()
  await expect(page.getByText('169 条来源记录', { exact: false })).toBeVisible()
  await expect(page.getByText('退款待处理 4', { exact: true })).toBeVisible()
  await assertNoHorizontalOverflow(page)
})
