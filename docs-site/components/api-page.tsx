import { openapi } from '@/lib/openapi';
import { OpenAPIPage } from './api-client';

export async function APIPage({ document }: { document: string }) {
  const schemas = await openapi.getSchemas();
  return (
    <OpenAPIPage
      document={document}
      preloaded={{
        docs: Object.fromEntries(Object.entries(schemas).map(([id, schema]) => [id, schema.bundled])),
      }}
    />
  );
}
