import { createOpenAPI } from 'fumadocs-openapi/server';
import path from 'node:path';

export const openapi = createOpenAPI({
  input: {
    pockettally: path.resolve('.generated-content/contracts/openapi.yaml'),
  },
});
