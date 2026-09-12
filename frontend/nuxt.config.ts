import { appearanceBootScript, COLOR_MODE_STORAGE_KEY } from './app/constants/appearance'

export default defineNuxtConfig({
  compatibilityDate: '2026-09-07',
  devtools: { enabled: true },
  runtimeConfig: { apiBase: 'http://127.0.0.1:8000' },
  nitro: { preset: 'bun' },
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css', '~/assets/css/mvp.css', '~/assets/css/theme.css', '~/assets/css/layout.css', '~/assets/css/resource-editor.css'],
  colorMode: {
    preference: 'system',
    fallback: 'light',
    classSuffix: '',
    dataValue: 'theme',
    storage: 'localStorage',
    storageKey: COLOR_MODE_STORAGE_KEY,
  },
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'PocketTally · 我的账本',
      meta: [
        { name: 'description', content: 'PocketTally 个人记账与统计工作台' },
      ],
      script: [
        { key: 'pockettally-appearance', innerHTML: appearanceBootScript },
      ],
    },
  },
})
