import { expect, test } from '@playwright/test'

const incomeDefaults = ['工资', '奖金', '兼职副业', '投资收益', '其他收入']
const expenseDefaults = ['餐饮', '交通', '住房', '生活缴费', '购物', '娱乐', '医疗', '教育', '通讯网络', '旅行', '人情往来', '其他支出']

test('新账本首次使用：默认分类可见并可用于记账', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()

  await page.getByRole('link', { name: '分类与标签', exact: true }).click()
  const expenseTree = page.getByRole('tree', { name: '支出分类树' })
  for (const category of expenseDefaults) {
    await expect(expenseTree).toContainText(category)
  }

  await page.getByRole('tab', { name: /收入分类/ }).click()
  const incomeTree = page.getByRole('tree', { name: '收入分类树' })
  for (const category of incomeDefaults) {
    await expect(incomeTree).toContainText(category)
  }

  await page.getByRole('link', { name: '总览', exact: true }).click()
  await page.getByRole('button', { name: '记一笔', exact: true }).click()
  await page.getByRole('dialog').last().getByRole('button', { name: '餐饮，选择分类' }).click()
  await expect(page.getByRole('dialog').last()).toContainText('餐饮')
})
