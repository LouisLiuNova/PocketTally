import { expect, test } from '@playwright/test'

test('快捷记账：多层分类、金额计算、失败保留及连续保存', async ({ page }) => {
  await page.setViewportSize({ width: 729, height: 480 })
  const suffix = Date.now().toString()
  const api = 'http://127.0.0.1:8012/api/v1'
  const create = async (path: string, data: object) => {
    const response = await page.request.post(`${api}/${path}`, { data })
    expect(response.ok(), await response.text()).toBe(true)
    return response.json() as Promise<{ id: string }>
  }
  const account = await create('accounts', { name: `快捷账户${suffix}`, type: 'debit' })
  await create('transactions', { type: 'balance_adjustment', sourceAccountId: account.id, amount: 1000, balanceAdjustmentDirection: 'increase', occurredAt: new Date().toISOString() })
  const rootName = `快捷父级${suffix}`
  const childName = `快捷子级${suffix}`
  const grandchildName = `快捷末级${suffix}`
  const root = await create('categories', { name: rootName, purpose: 'expense', iconName: 'i-lucide-folder', iconColor: '#005CAF' })
  const child = await create('categories', { name: childName, purpose: 'expense', parentCategoryId: root.id, iconName: 'i-lucide-coffee', iconColor: '#005CAF' })
  const grandchild = await create('categories', { name: grandchildName, purpose: 'expense', parentCategoryId: child.id, iconName: 'i-lucide-coffee', iconColor: '#005CAF' })
  const tag = await create('tags', { name: `快捷标签${suffix}`, color: '#005CAF' })
  const posts: Record<string, unknown>[] = []
  let failOnce = true
  await page.route('**/api/v1/transactions', async route => {
    if (route.request().method() !== 'POST') { await route.continue(); return }
    posts.push(route.request().postDataJSON() as Record<string, unknown>)
    if (failOnce) { failOnce = false; await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"暂时无法保存"}' }); return }
    await route.continue()
  })

  await page.goto('/transactions')
  await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
  await expect(page.getByRole('button', { name: '记一笔', exact: true }).first()).toBeEnabled()
  await page.getByRole('button', { name: '记一笔', exact: true }).first().click()
  const dialog = page.getByRole('dialog').last()
  await expect(dialog.getByRole('button', { name: '完成', exact: true })).toBeVisible()
  await expect(dialog.getByRole('button', { name: '保存再记', exact: true })).toBeVisible()
  await dialog.getByRole('button', { name: `${rootName}，查看子分类` }).click()
  await dialog.getByRole('button', { name: `${childName}，查看子分类` }).click()
  await dialog.getByRole('button', { name: '返回上级' }).click()
  await dialog.getByRole('button', { name: `${childName}，查看子分类` }).click()
  await dialog.getByRole('button', { name: `${grandchildName}，选择分类` }).click()
  await expect(dialog).toContainText(`已选择：${grandchildName}`)
  await dialog.getByLabel('账户', { exact: true }).click()
  await page.getByRole('option', { name: `快捷账户${suffix} · ¥1,000.00` }).click()
  await dialog.getByLabel('金额（元）', { exact: true }).fill('12.34')
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '+' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '0' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '.' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '6' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '计算结果' }).click()
  await expect(dialog.getByLabel('金额（元）', { exact: true })).toHaveValue('12.94')
  await dialog.getByLabel('说明', { exact: true }).fill(`第一笔${suffix}`)
  await dialog.getByLabel(`快捷标签${suffix}`).check()
  await dialog.getByRole('button', { name: '保存再记' }).click()
  await expect(dialog.getByRole('alert')).toBeVisible()
  await expect(dialog.getByLabel('金额（元）', { exact: true })).toHaveValue('12.94')
  await expect(dialog.getByLabel('说明', { exact: true })).toHaveValue(`第一笔${suffix}`)
  await dialog.getByRole('button', { name: '保存再记' }).click()
  await expect(dialog.getByLabel('金额（元）', { exact: true })).toHaveValue('')
  await expect(dialog.getByLabel('说明', { exact: true })).toHaveValue('')
  await expect(dialog).toContainText(`已选择：${grandchildName}`)
  await expect(dialog.getByLabel(`快捷标签${suffix}`)).toBeChecked()
  await dialog.getByLabel('金额（元）', { exact: true }).fill('2')
  await dialog.getByRole('button', { name: '完成', exact: true }).click()
  await expect(dialog).toBeHidden()
  expect(posts).toHaveLength(3)
  expect(posts[1]).toMatchObject({ type: 'expense', amount: 12.94, sourceAccountId: account.id, categoryId: grandchild.id, tagIds: [tag.id], description: `第一笔${suffix}` })
  expect(posts[2]).toMatchObject({ type: 'expense', amount: 2, sourceAccountId: account.id, categoryId: grandchild.id, tagIds: [tag.id], description: null })
  await page.getByLabel('搜索交易', { exact: true }).fill(`第一笔${suffix}`)
  await expect(page.getByText(`第一笔${suffix}`, { exact: true })).toBeVisible()
})

test('分类父级可直接选择，返回与类型切换清理旧选择', async ({ page }) => {
  const suffix = Date.now().toString()
  const rootName = `切换父级${suffix}`
  const response = await page.request.post('http://127.0.0.1:8012/api/v1/categories', { data: { name: rootName, purpose: 'expense', iconName: 'i-lucide-folder', iconColor: '#005CAF' } })
  expect(response.ok(), await response.text()).toBe(true)
  const rootCategory = await response.json() as { id: string }
  const child = await page.request.post('http://127.0.0.1:8012/api/v1/categories', { data: { name: `切换子级${suffix}`, purpose: 'expense', parentCategoryId: rootCategory.id, iconName: 'i-lucide-folder', iconColor: '#005CAF' } })
  expect(child.ok(), await child.text()).toBe(true)
  await page.goto('/')
  await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
  await page.getByRole('button', { name: '记一笔', exact: true }).click()
  const dialog = page.getByRole('dialog').last()
  const root = dialog.getByRole('button', { name: `${rootName}，查看子分类` })
  await root.click()
  await expect(dialog.getByRole('button', { name: `选择当前分类：${rootName}` })).toBeVisible()
  await dialog.getByRole('button', { name: '取消', exact: true }).click()
  await root.click()
  await dialog.getByRole('button', { name: '返回上级' }).click()
  await root.click()
  await dialog.getByRole('button', { name: `选择当前分类：${rootName}` }).click()
  await expect(dialog).toContainText(`已选择：${rootName}`)
  await dialog.getByRole('radio', { name: '收入', exact: true }).click()
  await expect(dialog.getByText(`已选择：${rootName}`)).toHaveCount(0)
  await dialog.getByRole('button', { name: '工资，选择分类' }).click()
  await expect(dialog).toContainText('已选择：工资')
  await dialog.getByRole('radio', { name: '支出', exact: true }).click()
  await expect(dialog.getByText('已选择：工资')).toHaveCount(0)
})
