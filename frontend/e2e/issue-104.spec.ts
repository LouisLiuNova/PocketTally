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
  await expect(dialog.getByLabel('金额（元）', { exact: true })).toHaveValue('')
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '0' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '.' }).click()
  await dialog.getByRole('group', { name: '金额键盘' }).getByRole('button', { name: '6' }).click()
  await expect(dialog.getByLabel('待计算算式', { exact: true })).toHaveText('12.34 + 0.6')
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

for (const viewport of [{ width: 1440, height: 900 }, { width: 375, height: 667 }]) {
  test(`快捷表单 ${viewport.width}×${viewport.height}：键盘算式、直接保存、草稿保留与焦点`, async ({ page }) => {
    await page.setViewportSize(viewport)
    const suffix = `${viewport.width}-${Date.now()}`
    const create = async (path: string, data: object) => {
      const response = await page.request.post(`http://127.0.0.1:8012/api/v1/${path}`, { data })
      expect(response.ok(), await response.text()).toBe(true)
      return response.json() as Promise<{ id: string }>
    }
    const accountName = `计算账户${suffix}`
    const account = await create('accounts', { name: accountName, type: 'debit' })
    await create('transactions', { type: 'balance_adjustment', sourceAccountId: account.id, amount: 1000, balanceAdjustmentDirection: 'increase', occurredAt: new Date().toISOString() })
    const posts: Record<string, unknown>[] = []
    let failOnce = true
    await page.route('**/api/v1/transactions', async route => {
      if (route.request().method() !== 'POST') { await route.continue(); return }
      posts.push(route.request().postDataJSON() as Record<string, unknown>)
      if (failOnce) { failOnce = false; await route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"演示保存失败"}' }); return }
      await route.continue()
    })
    await page.goto('/transactions')
    await page.waitForFunction(() => Boolean((document.querySelector('#__nuxt') as HTMLElement & { __vue_app__?: unknown } | null)?.__vue_app__))
    const trigger = page.getByRole('button', { name: '记一笔', exact: true }).first()
    await trigger.click()
    const dialog = page.getByRole('dialog').last()
    const input = dialog.getByLabel('金额（元）', { exact: true })
    const keypad = dialog.getByRole('group', { name: '金额键盘' })
    await expect(dialog.getByRole('button', { name: '餐饮，选择分类' })).toBeVisible()
    const fieldOrder = await dialog.evaluate(element => {
      const fields = [...element.querySelector('.transaction-editor-fields')!.children]
      return {
        category: fields.findIndex(field => field.querySelector('.transaction-category-picker')),
        amount: fields.findIndex(field => field.querySelector('.transaction-amount-input')),
      }
    })
    expect(fieldOrder.category).toBeLessThan(fieldOrder.amount)
    expect(fieldOrder.category).toBeGreaterThanOrEqual(0)
    const keypadLayout = await keypad.evaluate(element => ({
      columns: getComputedStyle(element).gridTemplateColumns.split(' ').length,
      sizes: [...element.querySelectorAll('button')].map(button => parseFloat(getComputedStyle(button).minHeight)),
    }))
    expect(keypadLayout.columns).toBe(4)
    expect(keypadLayout.sizes).toHaveLength(16)
    expect(keypadLayout.sizes.every(height => height >= 44)).toBe(true)
    await expect.poll(async () => keypad.evaluate(element => [...element.querySelectorAll('button')].every(button => button.getBoundingClientRect().height >= 43.99))).toBe(true)
    expect(await input.evaluate(element => parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(32)
    expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)

    await dialog.getByRole('button', { name: '餐饮，选择分类' }).click()
    await dialog.getByLabel('账户', { exact: true }).click()
    await page.getByRole('option', { name: `${accountName} · ¥1,000.00`, exact: true }).click()
    await input.fill('12.34')
    await input.press('+')
    await input.pressSequentially('0.60')
    await input.press('-')
    await expect(input).toHaveValue('')
    await input.pressSequentially('0.04')
    await expect(dialog.getByLabel('待计算算式')).toHaveText('12.34 + 0.60 - 0.04')
    await expect(input).toHaveValue('0.04')
    await keypad.getByRole('button', { name: '删除一位' }).click()
    await expect(input).toHaveValue('0.0')
    await keypad.getByRole('button', { name: '4', exact: true }).click()
    await input.press('Tab')
    expect(await dialog.evaluate(element => element.contains(document.activeElement))).toBe(true)
    await dialog.getByLabel('说明', { exact: true }).fill(`直接结算${suffix}`)
    const saveAgain = dialog.getByRole('button', { name: '保存再记', exact: true })
    await saveAgain.click()
    await expect(dialog.getByRole('alert')).toBeVisible()
    await expect(input).toHaveValue('0.04')
    await expect(dialog.getByLabel('待计算算式')).toHaveText('12.34 + 0.60 - 0.04')
    await expect(dialog.getByLabel('说明', { exact: true })).toHaveValue(`直接结算${suffix}`)
    const footer = await saveAgain.boundingBox()
    expect(footer!.y).toBeGreaterThanOrEqual(0)
    expect(footer!.y + footer!.height).toBeLessThanOrEqual(viewport.height)
    await saveAgain.click()
    await expect(input).toHaveValue('')
    await expect(dialog.getByLabel('待计算算式')).toHaveCount(0)
    await expect(dialog).toContainText('已选择：餐饮')
    expect(posts[1]).toMatchObject({ amount: 12.9, sourceAccountId: account.id, description: `直接结算${suffix}` })

    await input.fill('5')
    await input.press('+')
    await dialog.getByRole('button', { name: '完成', exact: true }).click()
    await expect(dialog.getByRole('alert')).toContainText('请输入运算金额')
    expect(posts).toHaveLength(2)
    await input.press('Backspace')
    await expect(input).toHaveValue('5')
    await keypad.getByRole('button', { name: '清空金额' }).click()
    await expect(input).toHaveValue('')
    await input.pressSequentially('2+3=')
    await expect(input).toHaveValue('5.00')
    await input.press('2')
    await expect(input).toHaveValue('2')
    await input.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(trigger).toBeFocused()

    await page.getByLabel('搜索交易', { exact: true }).fill(`直接结算${suffix}`)
    await page.getByRole('button').filter({ hasText: `直接结算${suffix}` }).click()
    await page.getByRole('button', { name: '编辑交易', exact: true }).click()
    const editor = page.getByRole('dialog').filter({ has: page.getByRole('heading', { name: '编辑交易', exact: true }) })
    await expect(editor.getByRole('group', { name: '金额键盘' })).toHaveCount(0)
    await expect(editor.getByLabel('金额（元）', { exact: true })).toHaveValue('12.9')
    expect(await editor.evaluate(element => {
      const fields = [...element.querySelector('.transaction-editor-fields')!.children]
      return fields.findIndex(field => field.querySelector('.transaction-category-picker')) < fields.findIndex(field => field.querySelector('.transaction-amount-input'))
    })).toBe(true)
    await editor.getByLabel('金额（元）', { exact: true }).fill('13')
    await editor.getByRole('button', { name: '保存交易', exact: true }).click()
    await expect(editor).toBeHidden()
  })
}

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
