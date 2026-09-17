import { docs } from '../.source/server';
import { loader } from 'fumadocs-core/source';

export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
});

export const searchablePages = () =>
  source.getPages().filter((page) => page.data.search !== false);

export const searchableSource = {
  ...source,
  getPages: searchablePages,
};
