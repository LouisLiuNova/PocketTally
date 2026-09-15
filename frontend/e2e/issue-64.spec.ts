import { expect, test } from '@playwright/test'

test.describe('Issue #64：分类图标选择', () => {
  test('可搜索选择图标并在历史图标编辑时保留未知值', async ({ page }) => {
    const suffix = Date.now().toString()
    const api = 'http://127.0.0.1:8012/api/v1/categories'
    const knownName = `图标分类${suffix}`
    const legacyName = `历史图标${suffix}`
    let createBody: { iconName?: string } | undefined
    let patchBody: { iconName?: string } | undefined

    await page.route('**/api/v1/categories', async route => {
      if (route.request().method() === 'POST') createBody = route.request().postDataJSON()
      await route.continue()
    })
    await page.goto('/categories')
    await page.getByRole('button', { name: '新建分类', exact: true }).click()
    const dialog = page.getByRole('dialog').last()
    await dialog.getByLabel('名称', { exact: true }).fill(knownName)
    const iconPicker = dialog.getByRole('combobox', { name: '分类图标', exact: true })
    await iconPicker.click()
    await iconPicker.fill('咖啡')
    await page.getByRole('option', { name: '咖啡', exact: true }).click()
    await expect(dialog.locator('.category-icon-preview')).toContainText('咖啡')
    await dialog.getByRole('button', { name: '保存', exact: true }).click()
    await expect(page.getByRole('treeitem', { name: new RegExp(knownName) })).toBeVisible()
    expect(createBody?.iconName).toBe('i-lucide-coffee')

    const legacyResponse = await page.request.post(api, {
      data: { name: legacyName, purpose: 'expense', iconColor: '#005CAF', iconName: 'i-lucide-history-legacy' },
    })
    expect(legacyResponse.ok()).toBe(true)
    await page.reload()
    const legacyRow = page.getByRole('treeitem', { name: new RegExp(legacyName) })
    await legacyRow.locator('xpath=..').getByRole('button', { name: `更多操作：${legacyName}`, exact: true }).click()
    await page.getByRole('menuitem', { name: '编辑', exact: true }).click()
    const editDialog = page.getByRole('dialog').last()
    await expect(editDialog.locator('.category-icon-preview')).toContainText('历史图标')
    await page.route('**/api/v1/categories/*', async route => {
      if (route.request().method() === 'PATCH') patchBody = route.request().postDataJSON()
      await route.continue()
    })
    await editDialog.getByRole('button', { name: '保存', exact: true }).click()
    await expect(editDialog).toBeHidden()
    expect(patchBody?.iconName).toBe('i-lucide-history-legacy')
  })
})
