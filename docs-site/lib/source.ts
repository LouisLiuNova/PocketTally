import { docs } from '../.source/server';
import { loader } from 'fumadocs-core/source';

export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
});

export const searchablePages = () =>
  source.getPages().filter((page) => page.data.search !== false && (
    page.url === '/docs' || page.url.startsWith('/docs/user/') || page.url === '/docs/user' ||
    page.url.startsWith('/docs/developer/') || page.url === '/docs/developer'
  ));

export const searchableSource = {
  ...source,
  getPages: searchablePages,
};
