import type { ReactNode } from 'react';
import { Providers } from './providers';
import './globals.css';

export const metadata = {
  title: {
    default: 'PocketTally 文档',
    template: '%s · PocketTally',
  },
  description: 'PocketTally 用户指南、开发者指南和接口契约。',
};

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="zh-CN" suppressHydrationWarning><body><Providers>{children}</Providers></body></html>;
}
