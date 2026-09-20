import { defineConfig } from '@playwright/test'

const desktopViewports = [1280, 1440, 1920] as const
const e2eDatabasePath = process.env.POCKET_TALLY_E2E_DATABASE_PATH || `../frontend/.data/e2e-${process.pid}.sqlite3`
const reuseExistingServer = process.env.CI === 'true'

export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 60000,
  globalSetup: './e2e/global-setup.ts',
  use: { baseURL: 'http://127.0.0.1:3012', storageState: './.data/auth-state.json', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: desktopViewports.map(width => ({
    name: `chromium-${width}`,
    use: { ...({ browserName: 'chromium' as const }), viewport: { width, height: 900 } },
  })),
  webServer: [
    { command: `cd ../backend && printf 'PocketTally-E2E-Password-2026!\nPocketTally-E2E-Password-2026!\n' | POCKET_TALLY_DATABASE_PATH=${e2eDatabasePath} POCKET_TALLY_AUTH_ENABLED=true uv run pocket-tally-auth init --username e2e-owner && POCKET_TALLY_DATABASE_PATH=${e2eDatabasePath} POCKET_TALLY_AUTH_ENABLED=true POCKET_TALLY_PUBLIC_ORIGIN=http://127.0.0.1:3012 uv run uvicorn app.main:app --port 8012`, url: 'http://127.0.0.1:8012/api/v1/health', reuseExistingServer, timeout: 120000 },
    { command: 'bun run build && HOST=127.0.0.1 PORT=3012 NUXT_API_BASE=http://127.0.0.1:8012 bun run preview', url: 'http://127.0.0.1:3012/', reuseExistingServer, timeout: 180000 },
  ],
})
