import { notFound } from 'next/navigation';
import { DocsPage, DocsBody } from 'fumadocs-ui/page';
import { source } from '@/lib/source';
import { getMDXComponents } from '@/components/mdx';

export function generateStaticParams() {
  return source.generateParams();
}

export default async function Page({ params }: { params: Promise<{ slug?: string[] }> }) {
  const { slug } = await params;
  const page = source.getPage(slug);
  if (!page) notFound();
  const Mdx = page.data.body;
  const section = slug?.[0] === 'user'
    ? '用户指南'
    : slug?.[0] === 'developer'
      ? '开发者文档'
      : 'PocketTally 文档';
  const isLanding = !slug?.length || slug.length === 1 && ['user', 'developer'].includes(slug[0]);

  return (
    <DocsPage className="docs-article" toc={page.data.toc} full={page.data.full} tableOfContent={{ style: 'clerk' }}>
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-fd-primary">{section}</p>
      <h1>{page.data.title}</h1>
      {page.data.description ? <p className="docs-description text-lg leading-8 text-fd-muted-foreground">{page.data.description}</p> : null}
      <DocsBody className={`docs-body${isLanding ? ' docs-index' : ''}`}><Mdx components={getMDXComponents()} /></DocsBody>
    </DocsPage>
  );
}
