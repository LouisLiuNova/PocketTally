import { createFromSource } from 'fumadocs-core/search/server';
import { searchableSource } from '@/lib/source';

export const revalidate = false;
export const { staticGET: GET } = createFromSource(() => searchableSource as never, {
  async buildIndex(page) {
    const structuredData = page.data.structuredData;
    return {
      title: page.data.title ?? page.url,
      description: page.data.description,
      url: page.url,
      id: page.url,
      structuredData: (typeof structuredData === 'function' ? await structuredData() : structuredData) ?? { headings: [], contents: [] },
      tag: page.url.startsWith('/docs/developer/') ? 'developer' : 'user',
    };
  },
});
