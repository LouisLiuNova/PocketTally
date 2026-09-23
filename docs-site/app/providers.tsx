'use client';

import type { ReactNode } from 'react';
import { RootProvider } from 'fumadocs-ui/provider/next';
import { usePathname } from 'next/navigation';

export function Providers({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const defaultTag = pathname.startsWith('/docs/developer') ? 'developer' : 'user';

  return <RootProvider
    search={{ options: { defaultTag, type: 'static', api: '/PocketTally/api/search' } }}
    i18n={{ translations: {
      'Search(search trigger)': '搜索文档',
      'Search(search dialog)': '搜索文档',
      'No results found(search dialog)': '没有找到相关内容',
      'On this page(table of contents)': '本页目录',
      'No Headings(table of contents)': '本页没有章节',
      'Next Page(pagination)': '下一页',
      'Previous Page(pagination)': '上一页',
      'Light(theme switcher)(aria-label)': '浅色',
      'Dark(theme switcher)(aria-label)': '深色',
      'System(theme switcher)(aria-label)': '跟随系统',
      'Copy Text(code block)(aria-label)': '复制代码',
      'Copied Text(code block)(aria-label)': '已复制',
      'Open Sidebar(sidebar)(aria-label)': '打开侧栏',
      'Collapse Sidebar(sidebar)(aria-label)': '收起侧栏',
      'Toggle Menu(mobile menu)(aria-label)': '切换菜单',
    } }}
  >{children}</RootProvider>;
}
