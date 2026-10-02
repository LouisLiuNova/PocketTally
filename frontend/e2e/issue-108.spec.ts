import { expect, test, type Page } from '@playwright/test'
import type { Account, Category, Tag } from '../app/types/ledger'
import { assertNoHorizontalOverflow } from './helpers/layout'

// 隔离可见资源，保留真实 POST 与 SQLite 写入，避免依赖预置分类或其他用例的数据。
async function emptyWorkspace(page: Page) {
  const resources = { accounts: [] as Account[], categories: [] as Category[], tags: [] as Tag[] }
  const control = { failRead: false, failSave: false, gate: null as Promise<void> | null }
  await page.goto('/transactions')
  await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
  for (const kind of ['accounts', 'categories', 'tags'] as const) {
    await page.route(`**/api/v1/${kind}`, async route => {
      if (route.request().method() === 'GET') {
        if (control.gate) await control.gate
        await route.fulfill(control.failRead
          ? { status: 500, json: { message: '资源读取暂时失败' } }
          : { json: resources[kind] })
      } else if (route.request().method() === 'POST') {
        if (control.failSave) { await route.fulfill({ status: 500, json: { message: '资源保存暂时失败' } }); return }
        const response = await route.fetch()
        expect(response.ok(), await response.text()).toBe(true)
        const resource = await response.json()
        resources[kind].push(resource)
        await route.fulfill({ response })
      } else await route.continue()
    })
  }
  const refreshed = page.waitForResponse(response => response.url().endsWith('/api/v1/tags'))
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await refreshed
  await expect(page.getByRole('button', { name: '记一笔', exact: true }).first()).toBeEnabled()
  await page.getByRole('button', { name: '记一笔', exact: true }).first().click()
  const editor = page.getByRole('dialog', { name: '交易表单', exact: true })
  await expect(editor.getByText('暂无账户，先创建账户后即可记账。', { exact: true })).toBeVisible()
  return { resources, control, editor }
}

for (const scenario of [{ width: 1440, height: 900, theme: 'light' }, { width: 375, height: 812, theme: 'dark' }] as const) {
  test(`空资源 ${scenario.width}/${scenario.theme}：原位创建、取消焦点、草稿与交易保存`, async ({ page }, testInfo) => {
    await page.setViewportSize(scenario)
    await page.addInitScript(theme => localStorage.setItem('pockettally-appearance', JSON.stringify({ theme, palette: 'ruri' })), scenario.theme)
    const { editor } = await emptyWorkspace(page)
    await expect(page.locator('html')).toHaveAttribute('data-theme', scenario.theme)
    const suffix = `${scenario.width}-${Date.now()}`
    await expect(editor.getByLabel('账户', { exact: true })).toBeDisabled()
    await expect(editor.getByText('暂无可选支出分类', { exact: true })).toBeVisible()
    await expect(editor.getByText('暂无标签，可直接保存。', { exact: true })).toBeVisible()
    await page.screenshot({ path: testInfo.outputPath('empty-resources.png') })
    await assertNoHorizontalOverflow(page)
    await editor.getByRole('radio', { name: '收入', exact: true }).check()
    await expect(editor.getByText('暂无可选收入分类', { exact: true })).toBeVisible()
    await editor.getByLabel('金额（元）', { exact: true }).fill('12.34')
    await editor.getByLabel('说明', { exact: true }).fill(`空资源草稿-${suffix}`)
    const date = await editor.getByLabel('发生时间', { exact: true }).inputValue()
    const trigger = editor.getByRole('button', { name: '新建账户', exact: true })
    await trigger.focus()
    await trigger.press('Enter')
    let resource = page.getByRole('dialog', { name: '新建账户', exact: true })
    await expect(resource.getByLabel('名称', { exact: true })).toBeFocused()
    for (let index = 0; index < 5; index++) {
      await page.keyboard.press('Tab')
      expect(await resource.evaluate(element => element.contains(document.activeElement))).toBe(true)
    }
    await page.keyboard.press('Escape')
    await expect(trigger).toBeFocused()
    await trigger.press('Space')
    await resource.getByLabel('名称', { exact: true }).fill(`空账户-${suffix}`)
    await resource.getByRole('button', { name: '保存', exact: true }).click()
    await expect(resource).toBeHidden()
    await expect(editor.getByLabel('收款账户', { exact: true })).toContainText(`空账户-${suffix}`)
    await expect(editor.getByLabel('收款账户', { exact: true })).toBeFocused()

    await editor.getByRole('button', { name: '新建收入分类', exact: true }).click()
    resource = page.getByRole('dialog', { name: '新建收入分类', exact: true })
    await expect(resource.getByLabel('用途', { exact: true })).toContainText('收入')
    await resource.getByLabel('父分类', { exact: true }).click()
    await expect(page.getByRole('option', { name: '顶级分类', exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
    await resource.getByLabel('名称', { exact: true }).fill(`空收入分类-${suffix}`)
    await resource.getByRole('button', { name: '保存', exact: true }).click()
    await expect(resource).toBeHidden()
    await expect(editor.getByRole('button', { name: `空收入分类-${suffix}，选择分类` })).toBeFocused()
    await expect(editor.locator('.transaction-category-selection')).toContainText(`空收入分类-${suffix}`)

    await editor.getByRole('button', { name: '新建标签', exact: true }).click()
    resource = page.getByRole('dialog', { name: '新建标签', exact: true })
    await resource.getByLabel('名称', { exact: true }).fill(`空标签-${suffix}`)
    await resource.getByRole('button', { name: '保存', exact: true }).click()
    await expect(resource).toBeHidden()
    await expect(editor.getByRole('checkbox', { name: `空标签-${suffix}` })).toBeChecked()
    await expect(editor.getByRole('checkbox', { name: `空标签-${suffix}` })).toBeFocused()
    await expect(editor.getByLabel('金额（元）', { exact: true })).toHaveValue('12.34')
    await expect(editor.getByLabel('说明', { exact: true })).toHaveValue(`空资源草稿-${suffix}`)
    await expect(editor.getByLabel('发生时间', { exact: true })).toHaveValue(date)
    await expect(editor.getByRole('radio', { name: '收入', exact: true })).toBeChecked()
    await page.screenshot({ path: testInfo.outputPath('created-resources.png') })

    let failSave = true
    await page.route('**/api/v1/transactions', async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return }
      expect(route.request().postDataJSON()).toMatchObject({ type: 'income', amount: 12.34, description: `空资源草稿-${suffix}` })
      if (failSave) { failSave = false; await route.fulfill({ status: 500, json: { message: '交易保存暂时失败' } }); return }
      await route.continue()
    })
    await editor.getByRole('button', { name: '完成', exact: true }).click()
    await expect(editor.getByRole('alert')).toContainText('交易保存暂时失败')
    await expect(editor.getByLabel('说明', { exact: true })).toHaveValue(`空资源草稿-${suffix}`)
    await editor.getByRole('button', { name: '完成', exact: true }).click()
    await expect(editor).toBeHidden()
  })
}

test('零/单账户转账：补建第二账户保留转出选择，标签可跳过', async ({ page }) => {
  const { editor, resources } = await emptyWorkspace(page)
  await editor.getByRole('radio', { name: '转账', exact: true }).check()
  await expect(editor.getByLabel('转出账户', { exact: true })).toBeDisabled()
  await expect(editor.getByLabel('转入账户', { exact: true })).toBeDisabled()
  await expect(editor.getByRole('button', { name: '新建账户', exact: true })).toHaveCount(1)
  for (let index = 0; index < 2; index++) {
    await editor.getByRole('button', { name: '新建账户', exact: true }).click()
    const resource = page.getByRole('dialog', { name: '新建账户', exact: true })
    await resource.getByLabel('名称', { exact: true }).fill(`转账空账户-${Date.now()}-${index}`)
    await resource.getByRole('button', { name: '保存', exact: true }).click()
    await expect(resource).toBeHidden()
    if (!index) {
      await expect(editor.getByText('转账需要两个不同账户，请再创建一个账户。', { exact: true })).toBeVisible()
      await expect(editor.getByLabel('转出账户', { exact: true })).toBeEnabled()
    }
  }
  await expect(editor.getByLabel('转出账户', { exact: true })).toContainText(resources.accounts[0]!.name)
  await expect(editor.getByLabel('转入账户', { exact: true })).toContainText(resources.accounts[1]!.name)
  const adjustment = await page.request.post('http://127.0.0.1:8012/api/v1/transactions', { data: {
    type: 'balance_adjustment', sourceAccountId: resources.accounts[0]!.id, amount: 100, balanceAdjustmentDirection: 'increase', occurredAt: new Date().toISOString(),
  } })
  expect(adjustment.ok(), await adjustment.text()).toBe(true)
  await editor.getByLabel('金额（元）', { exact: true }).fill('1')
  const posted = page.waitForRequest(request => request.method() === 'POST' && request.url().endsWith('/api/v1/transactions'))
  await editor.getByRole('button', { name: '完成', exact: true }).click()
  expect((await posted).postDataJSON()).toMatchObject({ tagIds: [], sourceAccountId: resources.accounts[0]!.id, destinationAccountId: resources.accounts[1]!.id })
  await expect(editor).toBeHidden()
})

test('资源创建失败、同步失败和重试：草稿保留且不重复创建', async ({ page }) => {
  const { editor, control, resources } = await emptyWorkspace(page)
  await editor.getByRole('radio', { name: '调账', exact: true }).check()
  await editor.getByLabel('金额（元）', { exact: true }).fill('7')
  await editor.getByLabel('说明', { exact: true }).fill('失败后保留的草稿')
  control.failSave = true
  await editor.getByRole('button', { name: '新建账户', exact: true }).click()
  const resource = page.getByRole('dialog', { name: '新建账户', exact: true })
  const name = `同步重试账户-${Date.now()}`
  await resource.getByLabel('名称', { exact: true }).fill(name)
  await resource.getByRole('button', { name: '保存', exact: true }).click()
  await expect(resource.getByRole('alert')).toContainText('资源保存暂时失败')
  await expect(resource.getByLabel('名称', { exact: true })).toHaveValue(name)
  control.failSave = false
  control.failRead = true
  let releaseSync!: () => void
  control.gate = new Promise<void>(resolve => { releaseSync = resolve })
  await resource.getByRole('button', { name: '保存', exact: true }).click()
  await expect(resource.getByText('正在同步新资源…', { exact: true })).toBeVisible()
  await expect(resource.getByRole('button', { name: '保存', exact: true })).toBeDisabled()
  await page.keyboard.press('Escape')
  await expect(resource).toBeVisible()
  releaseSync()
  control.gate = null
  await expect(resource).toBeHidden()
  await expect(editor.getByRole('alert')).toContainText(`已创建「${name}」`)
  await expect(editor.getByRole('button', { name: '新建账户', exact: true })).toHaveCount(0)
  await expect(editor.getByLabel('账户', { exact: true })).toBeDisabled()
  await expect(editor.getByRole('button', { name: '重试读取资源', exact: true })).toBeFocused()
  control.failRead = false
  let release!: () => void
  control.gate = new Promise<void>(resolve => { release = resolve })
  await editor.getByRole('button', { name: '重试读取资源', exact: true }).click()
  await expect(editor.getByText('正在更新账户、分类和标签…', { exact: true })).toBeVisible()
  await expect(editor.getByRole('button', { name: '重试读取资源', exact: true })).toBeDisabled()
  await expect(editor.getByRole('button', { name: '新建账户', exact: true })).toHaveCount(0)
  release()
  control.gate = null
  await expect(editor.getByLabel('账户', { exact: true })).toContainText(name)
  await expect(editor.getByRole('alert')).toHaveCount(0)
  await expect(editor.getByLabel('金额（元）', { exact: true })).toHaveValue('7')
  await expect(editor.getByLabel('说明', { exact: true })).toHaveValue('失败后保留的草稿')
  expect(resources.accounts).toHaveLength(1)
})

test('有缓存的刷新失败：保留账户选择和草稿，恢复后用途与筛选默认项仍有效', async ({ page }) => {
  const { editor, control, resources } = await emptyWorkspace(page)
  await editor.getByRole('radio', { name: '收入', exact: true }).check()
  await editor.getByRole('button', { name: '新建账户', exact: true }).click()
  const resource = page.getByRole('dialog', { name: '新建账户', exact: true })
  const accountName = `缓存账户-${Date.now()}`
  await resource.getByLabel('名称', { exact: true }).fill(accountName)
  await resource.getByRole('button', { name: '保存', exact: true }).click()
  await expect(resource).toBeHidden()
  await editor.getByLabel('说明', { exact: true }).fill('缓存草稿')
  await editor.getByLabel('金额（元）', { exact: true }).fill('8')
  control.failRead = true
  await page.getByRole('button', { name: '刷新', exact: true, includeHidden: true }).evaluate(element => (element as HTMLButtonElement).click())
  await expect(editor.getByRole('alert')).toContainText('当前显示上次成功读取的数据')
  await expect(editor.getByLabel('收款账户', { exact: true })).toContainText(accountName)
  await expect(editor.getByLabel('收款账户', { exact: true })).toBeEnabled()
  await expect(editor.getByRole('button', { name: '新建收入分类', exact: true })).toHaveCount(0)
  control.failRead = false
  // 只有支出分类时，收入分类仍应提示为空。
  const response = await page.request.post('http://127.0.0.1:8012/api/v1/categories', { data: { name: `仅支出-${Date.now()}`, purpose: 'expense' } })
  expect(response.ok(), await response.text()).toBe(true)
  resources.categories.push(await response.json())
  await editor.getByRole('button', { name: '重试读取资源', exact: true }).click()
  await expect(editor.getByRole('button', { name: '新建收入分类', exact: true })).toBeVisible()
  await expect(editor.getByLabel('说明', { exact: true })).toHaveValue('缓存草稿')
  await expect(editor.getByLabel('收款账户', { exact: true })).toContainText(accountName)
  await editor.getByRole('radio', { name: '支出', exact: true }).check()
  await expect(editor.getByRole('button', { name: `${resources.categories[0]!.name}，选择分类` })).toBeVisible()
  await editor.getByRole('button', { name: '关闭', exact: true }).click()
  if (!await page.getByLabel('账户筛选', { exact: true }).isVisible()) await page.getByRole('button', { name: /^高级筛选/ }).click()
  await expect(page.getByLabel('账户筛选', { exact: true }).locator('option').first()).toHaveText('所有账户')
  await expect(page.getByLabel('分类筛选', { exact: true }).locator('option').first()).toHaveText('所有分类')
  await expect(page.getByLabel('标签筛选', { exact: true }).locator('option').first()).toHaveText('所有标签')
})

test('首次加载与失败：读取完成前不能进入创建型空状态，重试后恢复', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/login')
  await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
  let release!: () => void
  let failRead = true
  const gate = new Promise<void>(resolve => { release = resolve })
  for (const kind of ['accounts', 'categories', 'tags']) {
    await page.route(`**/api/v1/${kind}`, async route => {
      await gate
      await route.fulfill(failRead ? { status: 500, json: { message: '首次读取失败' } } : { json: [] })
    })
  }
  await page.getByLabel('用户名').fill('e2e-owner')
  await page.getByRole('textbox', { name: '密码' }).fill('PocketTally-E2E-Password-2026!')
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await expect(page.getByText('正在从账本服务同步资源…', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '记一笔', exact: true }).first()).toBeDisabled()
  await expect(page.getByRole('button', { name: '创建第一个账户', exact: true })).toHaveCount(0)
  release()
  await expect(page.getByRole('alert').filter({ hasText: '首次读取失败' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: '记一笔', exact: true }).first()).toBeDisabled()
  failRead = false
  await page.getByRole('button', { name: '重试', exact: true }).first().click()
  await expect(page.getByRole('button', { name: '记一笔', exact: true }).first()).toBeEnabled()
  await page.getByRole('button', { name: '记一笔', exact: true }).first().click()
  await expect(page.getByRole('dialog', { name: '交易表单', exact: true }).getByRole('button', { name: '新建账户', exact: true })).toBeVisible()
})
