export const APP_ROUTES = [
  { path: '/', label: '总览', title: '我的账本', breadcrumb: '总览', icon: 'i-lucide-layout-dashboard' },
  { path: '/transactions', label: '交易', title: '交易', breadcrumb: '交易', icon: 'i-lucide-arrow-left-right' },
  { path: '/accounts', label: '账户', title: '账户', breadcrumb: '账户', icon: 'i-lucide-wallet-cards' },
  { path: '/categories', label: '分类与标签', title: '分类与标签', breadcrumb: '分类与标签', icon: 'i-lucide-shapes' },
  { path: '/statistics', label: '统计分析', title: '统计分析', breadcrumb: '统计分析', icon: 'i-lucide-chart-no-axes-combined' },
  { path: '/settings', label: '设置', title: '设置', breadcrumb: '设置', icon: 'i-lucide-settings' },
] as const

export type AppRoutePath = typeof APP_ROUTES[number]['path']

export function appRoute(path: string) {
  return APP_ROUTES.find(item => item.path === path) || APP_ROUTES[0]
}
