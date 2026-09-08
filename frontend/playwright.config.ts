import { defineConfig } from '@playwright/test'

const desktopViewports = [1280, 1440, 1920] as const
const e2eDatabasePath = process.env.POCKET_TALLY_E2E_DATABASE_PATH || `../frontend/.data/e2e-${process.pid}.sqlite3`

export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:3012', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: desktopViewports.map(width => ({
    name: `chromium-${width}`,
    use: { ...({ browserName: 'chromium' as const }), viewport: { width, height: 900 } },
  })),
  webServer: [
    { command: `cd ../backend && POCKET_TALLY_DATABASE_PATH=${e2eDatabasePath} uv run uvicorn app.main:app --port 8012`, url: 'http://127.0.0.1:8012/api/v1/accounts', reuseExistingServer: false, timeout: 120000 },
    { command: 'bun run build && HOST=127.0.0.1 PORT=3012 NUXT_API_BASE=http://127.0.0.1:8012 bun .output/server/index.mjs', url: 'http://127.0.0.1:3012/', reuseExistingServer: false, timeout: 180000 },
  ],
})
