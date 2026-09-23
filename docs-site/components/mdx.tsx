import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { ImageZoomProps } from 'fumadocs-ui/components/image-zoom';
import type { MDXComponents } from 'mdx/types';
import { Mermaid } from './mermaid';
import { APIPage } from './api-page';
import { ZoomableImage } from './zoomable-image';

export function getMDXComponents(components?: MDXComponents): MDXComponents {
  return { ...defaultMdxComponents, img: (props) => <ZoomableImage {...(props as ImageZoomProps)} />, Mermaid, OpenAPIPage: APIPage, ...components };
}
