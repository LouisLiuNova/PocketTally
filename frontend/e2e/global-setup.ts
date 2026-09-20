import { chromium, type FullConfig } from '@playwright/test'
import { mkdir } from 'node:fs/promises'

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL as string
  const statePath = './.data/auth-state.json'
  await mkdir('./.data', { recursive: true })
  const browser = await chromium.launch()
  const context = await browser.newContext({ baseURL })
  const page = await context.newPage()
  await page.goto('/login')
  await page.getByLabel('用户名').fill('e2e-owner')
  await page.getByRole('textbox', { name: '密码' }).fill('PocketTally-E2E-Password-2026!')
  await page.getByRole('button', { name: '登录' }).click()
  await page.waitForURL(url => !url.pathname.endsWith('/login'))
  await context.storageState({ path: statePath })
  await browser.close()
}
