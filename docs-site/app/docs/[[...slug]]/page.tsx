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

  return (
    <DocsPage toc={page.data.toc} full={page.data.full} tableOfContent={{ style: 'clerk' }}>
      <h1>{page.data.title}</h1>
      {page.data.description ? <p className="text-xl text-fd-muted-foreground">{page.data.description}</p> : null}
      <DocsBody><Mdx components={getMDXComponents()} /></DocsBody>
    </DocsPage>
  );
}
