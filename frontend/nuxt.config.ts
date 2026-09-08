export default defineNuxtConfig({
  compatibilityDate: '2026-09-07',
  devtools: { enabled: true },
  runtimeConfig: { apiBase: 'http://127.0.0.1:8000' },
  nitro: { preset: 'bun' },
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css', '~/assets/css/mvp.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN' },
      title: 'PocketTally · 我的账本',
      meta: [
        { name: 'description', content: 'PocketTally 个人记账与统计工作台' },
      ],
    },
  },
})
