import type { ReactNode } from 'react';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { source } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return <DocsLayout tree={source.getPageTree()} nav={{ title: 'PocketTally 文档' }} githubUrl="https://github.com/LouisLiuNova/PocketTally">{children}</DocsLayout>;
}
