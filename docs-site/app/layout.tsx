import type { ReactNode } from 'react';
import { Providers } from './providers';
import './globals.css';

const paletteBootScript = `(() => {
  const allowed = ['ruri', 'toki', 'matsuba', 'fuji', 'yamabuki', 'asagi', 'konkikyo', 'kurumi'];
  try {
    const saved = localStorage.getItem('pockettally-docs-palette');
    if (saved && allowed.includes(saved)) document.documentElement.dataset.palette = saved;
  } catch {}
})();`;

export const metadata = {
  title: {
    default: 'PocketTally 文档',
    template: '%s · PocketTally',
  },
  description: 'PocketTally 用户指南、开发者指南和接口契约。',
};

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="zh-CN" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: paletteBootScript }} /></head><body><Providers>{children}</Providers></body></html>;
}
