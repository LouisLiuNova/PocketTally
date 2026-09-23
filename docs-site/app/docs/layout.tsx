import type { ReactNode } from 'react';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { source } from '@/lib/source';
import { PalettePicker } from '@/components/palette-picker';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.getPageTree()}
      nav={{
        title: (
          <span className="inline-flex items-center gap-2.5 font-semibold tracking-tight">
            <span aria-hidden="true" className="flex size-7 items-center justify-center rounded-lg bg-fd-primary text-xs font-bold text-fd-primary-foreground shadow-sm">P</span>
            <span>PocketTally <span className="font-normal text-fd-muted-foreground">文档</span></span>
          </span>
        ),
      }}
      themeSwitch={{ mode: 'light-dark-system' }}
      sidebar={{ footer: <PalettePicker key="docs-palette-picker" /> }}
      githubUrl="https://github.com/LouisLiuNova/PocketTally"
    >
      {children}
    </DocsLayout>
  );
}
