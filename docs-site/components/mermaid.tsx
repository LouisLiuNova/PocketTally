'use client';

import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

export function Mermaid({ chart }: { chart: string }) {
  const id = useId().replaceAll(':', '');
  const [svg, setSvg] = useState<string>();

  useEffect(() => {
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default', fontFamily: 'inherit' });
    void mermaid.render(`mermaid-${id}`, chart).then(({ svg: rendered }) => setSvg(rendered));
  }, [chart, id]);

  return svg ? <div aria-label="Mermaid 图表" dangerouslySetInnerHTML={{ __html: svg }} /> : <pre>{chart}</pre>;
}
