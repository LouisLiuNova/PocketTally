import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:3012', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  webServer: [
    { command: 'cd ../backend && POCKET_TALLY_DATABASE_PATH=../frontend/.data/e2e.sqlite3 uv run uvicorn app.main:app --port 8012', url: 'http://127.0.0.1:8012/api/v1/accounts', reuseExistingServer: false },
    { command: 'NUXT_API_BASE=http://127.0.0.1:8012 bun run dev --port 3012', url: 'http://127.0.0.1:3012', reuseExistingServer: false },
  ],
})
