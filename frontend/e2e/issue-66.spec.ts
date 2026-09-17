import { expect, test } from '@playwright/test'

test.describe('Issue #66：新标签页首次加载卡片', () => {
  test('服务端首屏已有核心卡片数据，现金流趋势独立客户端加载', async ({ page }) => {
    const accountName = `首次加载账户-${Date.now()}`
    const created = await page.request.post('http://127.0.0.1:8012/api/v1/accounts', {
      data: { type: 'debit', name: accountName },
    })
    expect(created.ok()).toBe(true)

    const browserCoreApiRequests: string[] = []
    const browserCashFlowRequests: string[] = []
    const browserCashFlowResponses: number[] = []
    const consoleErrors: string[] = []
    const pageErrors: string[] = []
    page.on('request', request => {
      const url = request.url()
      if (!url.includes('/api/v1/')) return
      if (url.includes('/api/v1/statistics/cash-flow')) browserCashFlowRequests.push(url)
      else browserCoreApiRequests.push(url)
    })
    page.on('response', response => {
      if (response.url().includes('/api/v1/statistics/cash-flow')) browserCashFlowResponses.push(response.status())
    })
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()) })
    page.on('pageerror', error => pageErrors.push(error.message))
    const initialResponse = await page.goto('/')
    expect(initialResponse?.ok()).toBe(true)
    expect(await initialResponse?.text()).toContain('本期摘要')
    await expect(page.getByRole('region', { name: '本期摘要' })).toBeVisible()
    await expect(page.getByRole('button', { name: '记一笔', exact: true })).toBeEnabled()
    await expect(page.getByRole('status', { name: '正在读取当前账本状态' })).toHaveCount(0)
    await expect.poll(() => browserCashFlowRequests.length).toBe(1)
    await expect.poll(() => browserCashFlowResponses.length).toBe(1)
    expect(browserCashFlowResponses).toEqual([200])
    expect(browserCoreApiRequests).toEqual([])
    const responseEndMs = await page.evaluate(() => Math.round((performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming).responseEnd))
    console.log(`首次加载证据：${test.info().project.name}，HTML 响应 ${responseEndMs} ms，核心浏览器 API 请求 ${browserCoreApiRequests.length}，现金流 API 请求 ${browserCashFlowRequests.length}，Console 错误 ${consoleErrors.length}，页面错误 ${pageErrors.length}`)
    await test.info().attach('first-load-evidence.json', {
      body: Buffer.from(JSON.stringify({ browser: test.info().project.name, responseEndMs, browserCoreApiRequests, browserCashFlowRequests, browserCashFlowResponses, consoleErrors, pageErrors }, null, 2)),
      contentType: 'application/json',
    })

    browserCoreApiRequests.length = 0
    browserCashFlowRequests.length = 0
    browserCashFlowResponses.length = 0
    const refreshedResponse = await page.reload()
    expect(await refreshedResponse?.text()).toContain('本期摘要')
    await expect(page.getByRole('region', { name: '本期摘要' })).toBeVisible()
    await expect.poll(() => browserCashFlowRequests.length).toBe(1)
    await expect.poll(() => browserCashFlowResponses.length).toBe(1)
    expect(browserCashFlowResponses).toEqual([200])
    expect(browserCoreApiRequests).toEqual([])
    expect(consoleErrors).toEqual([])
    expect(pageErrors).toEqual([])

    const accountsResponse = await page.goto('/accounts')
    expect(await accountsResponse?.text()).toContain(accountName)
    await expect(page.locator('[data-account-id]').filter({ hasText: accountName })).toBeVisible()
  })

  test('客户端进入总览时慢响应展示加载状态，完成后自动显示卡片', async ({ page }) => {
    await page.goto('/accounts')
    let releaseResponse: () => void = () => {}
    const responseGate = new Promise<void>(resolve => { releaseResponse = resolve })
    await page.route('**/api/v1/statistics/overview?**', async route => {
      await responseGate
      await route.continue()
    })

    await page.getByRole('link', { name: '总览', exact: true }).click()
    await expect(page.getByRole('status', { name: '正在读取当前账本状态' })).toBeVisible()
    await expect(page.getByText('暂无交易', { exact: true })).toHaveCount(0)
    releaseResponse()
    await expect(page.getByRole('region', { name: '本期摘要' })).toBeVisible()
    await expect(page.getByRole('status', { name: '正在读取当前账本状态' })).toHaveCount(0)
  })

  test('客户端请求失败后显示错误并可重试恢复卡片', async ({ page }) => {
    await page.goto('/accounts')
    await page.route('**/api/v1/statistics/overview?**', route => route.abort())
    await page.getByRole('link', { name: '总览', exact: true }).click()
    await expect(page.getByRole('alert')).toContainText('总览读取失败')
    await expect(page.getByRole('region', { name: '本期摘要' })).toHaveCount(0)

    await page.unroute('**/api/v1/statistics/overview?**')
    await page.getByRole('button', { name: '重试', exact: true }).click()
    await expect(page.getByRole('region', { name: '本期摘要' })).toBeVisible()
    await expect(page.getByRole('alert')).toHaveCount(0)
  })
})
