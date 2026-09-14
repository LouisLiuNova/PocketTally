import { expect, test } from '@playwright/test'

test('Issue #56：创建顶级分类后弹窗关闭并即时显示', async ({ page }) => {
  const suffix = Date.now().toString()
  const name = `顶级分类回归${suffix}`
  const pageErrors: string[] = []
  const consoleErrors: string[] = []
  let requestBody: { parentCategoryId?: string | null } | undefined

  page.on('pageerror', error => pageErrors.push(error.message))
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  await page.route('**/api/v1/categories', async route => {
    if (route.request().method() === 'POST') requestBody = route.request().postDataJSON()
    await route.continue()
  })

  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await page.getByRole('link', { name: '分类与标签', exact: true }).click()
  await page.getByRole('button', { name: '新建分类', exact: true }).click()
  const dialog = page.getByRole('dialog').last()
  await dialog.getByLabel('名称', { exact: true }).fill(name)
  await expect(dialog.getByLabel('父分类', { exact: true })).toContainText('顶级分类')
  await dialog.getByRole('button', { name: '保存', exact: true }).click()

  await expect(dialog).toBeHidden()
  await expect(page.getByText('保存成功', { exact: true })).toBeVisible()
  await expect(page.getByRole('treeitem', { name: new RegExp(name) })).toBeVisible()
  expect(requestBody?.parentCategoryId).toBeNull()
  expect(pageErrors).toEqual([])
  expect(consoleErrors.filter(error => error.includes('SelectItem') || error.includes('卸载') || error.includes('unmount'))).toEqual([])
})
