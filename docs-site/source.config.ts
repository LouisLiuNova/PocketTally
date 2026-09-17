import { defineDocs, frontmatterSchema } from 'fumadocs-mdx/config';
import { z } from 'zod';

export const docs = defineDocs({
  dir: '.generated-content/docs',
  docs: {
    schema: frontmatterSchema.extend({
      search: z.boolean().optional(),
      historical: z.boolean().optional(),
    }),
  },
});
