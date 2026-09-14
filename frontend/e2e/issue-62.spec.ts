import { expect, test } from '@playwright/test'

test.describe('Issue #62：交易类型一键切换', () => {
  test('单击和键盘操作四种类型，并切换对应字段', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: '记一笔', exact: true }).click()
    const dialog = page.getByRole('dialog').last()
    const radios = dialog.getByRole('radio')
    await expect(radios).toHaveCount(4)

    await dialog.getByRole('radio', { name: '收入', exact: true }).click()
    await expect(dialog.getByLabel('收款账户', { exact: true })).toBeVisible()
    await expect(dialog.getByLabel('账户', { exact: true })).toHaveCount(0)

    await dialog.getByRole('radio', { name: '转账', exact: true }).click()
    await expect(dialog.getByLabel('转出账户', { exact: true })).toBeVisible()
    await expect(dialog.getByLabel('转入账户', { exact: true })).toBeVisible()

    await dialog.getByRole('radio', { name: '调账', exact: true }).focus()
    await dialog.getByRole('radio', { name: '调账', exact: true }).press('ArrowLeft')
    await expect(dialog.getByRole('radio', { name: '转账', exact: true })).toBeChecked()

    await dialog.getByRole('radio', { name: '支出', exact: true }).click()
    await expect(dialog.getByLabel('分类', { exact: true })).toBeVisible()
    await expect(dialog.getByLabel('调整方向', { exact: true })).toHaveCount(0)
    await expect(dialog.getByRole('radio', { name: '支出', exact: true })).toBeChecked()
  })
})
