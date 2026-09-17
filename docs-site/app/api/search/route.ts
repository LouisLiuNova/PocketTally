import { createFromSource } from 'fumadocs-core/search/server';
import { searchableSource } from '@/lib/source';

export const revalidate = false;
export const { staticGET: GET } = createFromSource(() => searchableSource as never);
