import { expect, test, type Locator } from '@playwright/test'

async function setNativeColor(locator: Locator, value: string) {
  await locator.evaluate((element, nextValue) => {
    element.value = nextValue
    element.dispatchEvent(new Event('input', { bubbles: true }))
  }, value)
}

test('分类和标签支持 HEX/RGB 双向选色、字段校验与编辑回填', async ({ page }) => {
  const suffix = Date.now().toString()
  const category = `颜色分类${suffix}`
  const tag = `颜色标签${suffix}`
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
  await page.getByRole('link', { name: '分类与标签', exact: true }).click()

  await page.getByRole('button', { name: '新建分类', exact: true }).click()
  let dialog = page.getByRole('dialog').last()
  const categoryColor = dialog.getByLabel('颜色值（#RRGGBB）', { exact: true })
  const categoryPicker = dialog.getByLabel('颜色选择器', { exact: true })
  await expect(categoryColor).toHaveValue('#005CAF')
  await categoryColor.fill('#abcdef')
  await expect(categoryPicker).toHaveValue('#abcdef')
  await expect(dialog.locator('.color-input-preview')).toHaveCSS('background-color', 'rgb(171, 205, 239)')
  await setNativeColor(categoryPicker, '#123456')
  await expect(categoryColor).toHaveValue('#123456')

  let categoryWrites = 0
  await page.route('**/api/v1/categories', async route => {
    if (route.request().method() === 'POST') categoryWrites += 1
    await route.continue()
  })
  await categoryColor.fill('#12GG56')
  await expect(dialog).toContainText('颜色值只能包含十六进制字符')
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(dialog).toBeVisible()
  await expect(categoryColor).toHaveValue('#12GG56')
  expect(categoryWrites).toBe(0)
  await categoryColor.fill('#005CAF')
  await dialog.getByLabel('名称', { exact: true }).fill(category)
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByText(category, { exact: true })).toBeVisible()

  const categoryRow = page.locator('.resource-row').filter({ has: page.getByText(category, { exact: true }) })
  await categoryRow.getByRole('button', { name: '编辑', exact: true }).click()
  dialog = page.getByRole('dialog').last()
  await expect(dialog.getByLabel('颜色值（#RRGGBB）', { exact: true })).toHaveValue('#005CAF')
  await dialog.getByLabel('颜色值（#RRGGBB）', { exact: true }).fill('#abcdef')
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByText(category, { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '新建标签', exact: true }).click()
  dialog = page.getByRole('dialog').last()
  const tagColor = dialog.getByLabel('颜色值（#RRGGBB）', { exact: true })
  await tagColor.fill('#12345')
  await expect(dialog).toContainText('颜色值必须是 6 位十六进制颜色')
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(dialog).toBeVisible()
  await tagColor.fill('#abcdef')
  await dialog.getByLabel('名称', { exact: true }).fill(tag)
  await dialog.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByText(tag, { exact: true })).toBeVisible()
  const tagRow = page.locator('.resource-row').filter({ has: page.getByText(tag, { exact: true }) })
  await tagRow.getByRole('button', { name: '编辑', exact: true }).click()
  dialog = page.getByRole('dialog').last()
  await expect(dialog.getByLabel('颜色值（#RRGGBB）', { exact: true })).toHaveValue('#abcdef')
  await page.reload()
  await page.getByRole('link', { name: '分类与标签', exact: true }).click()
  await expect(page.getByRole('treeitem', { name: new RegExp(category) }).locator('.category-icon')).toHaveCSS('color', 'rgb(171, 205, 239)')
  await expect(page.locator('.resource-row').filter({ has: page.getByText(tag, { exact: true }) }).locator('.color-dot')).toHaveCSS('background-color', 'rgb(171, 205, 239)')
  await expect(page.locator('.resource-row').filter({ has: page.getByText(tag, { exact: true }) })).toContainText(tag)
})
