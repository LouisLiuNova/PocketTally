'use client';

import { ImageZoom, type ImageZoomProps } from 'fumadocs-ui/components/image-zoom';

export function ZoomableImage(props: ImageZoomProps) {
  return (
    <ImageZoom
      {...props}
      role="button"
      tabIndex={0}
      aria-label={`放大图片：${props.alt || '文档图片'}`}
      className={`${props.className || ''} rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary`}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          event.currentTarget.click();
        }
      }}
    />
  );
}
