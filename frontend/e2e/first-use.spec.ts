import { expect, test, type Page } from '@playwright/test'

async function selectOption(page: Page, label: string, option: string) {
  await page.getByRole('dialog').last().getByLabel(label, { exact: true }).click()
  await page.getByRole('option', { name: option, exact: true }).click()
}

test('全新账本无需创建分类即可录入第一笔收入和支出', async ({ page }) => {
  const suffix = Date.now().toString()
  const account = `首次使用账户${suffix}`
  const incomeDescription = `首次工资${suffix}`
  const expenseDescription = `首次餐饮${suffix}`

  await page.goto('/categories')
  await expect(page.getByText('餐饮', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: /收入分类/ }).click()
  await expect(page.getByText('工资', { exact: true })).toBeVisible()

  await page.goto('/accounts')
  await page.getByRole('button', { name: '新建账户', exact: true }).click()
  await page.getByLabel('名称', { exact: true }).fill(account)
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await expect(page.getByText(account, { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '记一笔', exact: true }).click()
  await selectOption(page, '交易类型', '收入')
  await page.getByLabel('金额（元）', { exact: true }).fill('100')
  await page.getByLabel('说明', { exact: true }).fill(incomeDescription)
  await selectOption(page, '收款账户', account)
  await selectOption(page, '分类', '工资')
  await page.getByRole('button', { name: '保存交易', exact: true }).click()
  await expect(page.getByRole('button', { name: '保存交易', exact: true })).toBeHidden()

  await page.getByRole('button', { name: '记一笔', exact: true }).click()
  await page.getByLabel('金额（元）', { exact: true }).fill('20')
  await page.getByLabel('说明', { exact: true }).fill(expenseDescription)
  await page.getByRole('dialog').last().getByLabel('账户', { exact: true }).click()
  const accountOption = await page.getByRole('option').allTextContents()
  await page.getByRole('option', {
    name: accountOption.find(value => value.startsWith(account))!,
    exact: true,
  }).click()
  await selectOption(page, '分类', '餐饮')
  await page.getByRole('button', { name: '保存交易', exact: true }).click()
  await expect(page.getByRole('button', { name: '保存交易', exact: true })).toBeHidden()

  await page.goto('/transactions')
  await expect(page.getByText(incomeDescription, { exact: true })).toBeVisible()
  await expect(page.getByText(expenseDescription, { exact: true })).toBeVisible()
})
