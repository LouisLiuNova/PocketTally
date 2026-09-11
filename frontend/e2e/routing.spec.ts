import { expect, test } from '@playwright/test'

const routes = [
  { path: '/', label: '总览', title: '我的账本' },
  { path: '/transactions', label: '交易', title: '交易' },
  { path: '/accounts', label: '账户', title: '账户' },
  { path: '/categories', label: '分类与标签', title: '分类与标签' },
  { path: '/statistics', label: '统计分析', title: '统计分析' },
  { path: '/settings', label: '设置', title: '设置' },
]

test('六个页面可直接访问，标题与导航选中态来自路由', async ({ page }) => {
  for (const item of routes) {
    await page.goto(item.path)
    await expect(page.getByRole('heading', { level: 1, name: item.title, exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: item.label, exact: true })).toHaveAttribute('aria-current', 'page')
    await expect(page).toHaveTitle(`PocketTally · ${item.title}`)
    await page.reload()
    await expect(page.getByRole('link', { name: item.label, exact: true })).toHaveAttribute('aria-current', 'page')
  }
  await expect(page.getByRole('heading', { name: '主题模式', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '外观设置', exact: true })).toHaveCount(0)
  const themeGroup = page.getByRole('radiogroup', { name: '主题模式', exact: true })
  await expect(themeGroup).toBeVisible()
  await expect(themeGroup.getByRole('radio')).toHaveCount(3)
})

test('交易筛选可规范化、刷新及前进后退恢复', async ({ page }) => {
  await page.goto('/transactions?unknown=value&page=-2&type=missing&accountId=invalid')
  await expect.poll(() => new URL(page.url()).search).toBe('')

  await page.getByLabel('状态筛选').selectOption('all')
  await expect.poll(() => new URL(page.url()).searchParams.get('status')).toBe('all')
  await page.getByLabel('搜索交易').fill('  路由搜索  ')
  await expect.poll(() => new URL(page.url()).searchParams.get('q')).toBe('路由搜索')
  await page.reload()
  await expect(page.getByLabel('状态筛选')).toHaveValue('all')
  await expect(page.getByLabel('搜索交易')).toHaveValue('路由搜索')

  await page.goBack()
  await expect.poll(() => new URL(page.url()).search).toBe('')
  await expect(page.getByLabel('状态筛选')).toHaveValue('active')
  await expect(page.getByLabel('搜索交易')).toHaveValue('')
  await page.goForward()
  await expect(page.getByLabel('状态筛选')).toHaveValue('all')
  await expect(page.getByLabel('搜索交易')).toHaveValue('路由搜索')
})

test('交易日期支持显式无边界，统计自定义范围可恢复并显示专属空状态', async ({ page }) => {
  await page.goto('/transactions?start=&end=')
  await expect(page.getByLabel('开始日期')).toHaveValue('')
  await expect(page.getByLabel('结束日期（不含）')).toHaveValue('')
  await page.reload()
  await expect(page.getByLabel('开始日期')).toHaveValue('')
  await expect(page.getByLabel('结束日期（不含）')).toHaveValue('')

  await page.goto('/statistics?preset=custom&start=2099-01-01&end=2099-02-01&granularity=month&unknown=value')
  await expect.poll(() => new URL(page.url()).searchParams.has('unknown')).toBe(false)
  await expect(page.getByLabel('开始')).toHaveValue('2099-01-01')
  await expect(page.getByLabel('结束（不含）')).toHaveValue('2099-02-01')
  await expect(page.getByLabel('粒度')).toHaveValue('month')
  await expect(page.getByText('当前筛选范围暂无可分析数据', { exact: true })).toBeVisible()
  await expect(page.getByText('欢迎来到你的账本', { exact: true })).toBeHidden()
})

test('交易页不会请求统计接口', async ({ page }) => {
  let statisticsRequests = 0
  page.on('request', request => {
    if (request.url().includes('/api/v1/statistics/')) statisticsRequests++
  })
  await page.goto('/transactions')
  await expect(page.getByText(/服务端共 \d+ 笔/)).toBeVisible()
  expect(statisticsRequests).toBe(0)
})
