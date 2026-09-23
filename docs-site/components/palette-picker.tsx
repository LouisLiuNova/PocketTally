'use client';

import { useEffect, useState } from 'react';

const STORAGE_KEY = 'pockettally-docs-palette';
const PALETTES = [
  { value: 'ruri', label: '瑠璃浅葱', color: '#075eb1' },
  { value: 'toki', label: '朱鷺色', color: '#b02d2b' },
  { value: 'matsuba', label: '松葉色', color: '#3c6a1c' },
  { value: 'fuji', label: '藤紫', color: '#694fa3' },
  { value: 'yamabuki', label: '山吹', color: '#855300' },
  { value: 'asagi', label: '浅葱', color: '#006972' },
  { value: 'konkikyo', label: '紺桔梗', color: '#4b57a9' },
  { value: 'kurumi', label: '胡桃', color: '#96490c' },
] as const;

type Palette = typeof PALETTES[number]['value'];

function isPalette(value: string | undefined): value is Palette {
  return PALETTES.some((palette) => palette.value === value);
}

export function PalettePicker() {
  const [selected, setSelected] = useState<Palette>('ruri');

  useEffect(() => {
    const palette = document.documentElement.dataset.palette;
    if (isPalette(palette)) setSelected(palette);
  }, []);

  function selectPalette(palette: Palette) {
    document.documentElement.dataset.palette = palette;
    setSelected(palette);
    try {
      localStorage.setItem(STORAGE_KEY, palette);
    } catch {
      // Keep the current selection for this page even when storage is unavailable.
    }
  }

  const current = PALETTES.find((palette) => palette.value === selected) ?? PALETTES[0];

  return (
    <details className="docs-palette-picker">
      <summary className="docs-palette-trigger" aria-label={`主题色：${current.label}`}>
        <span aria-hidden="true" className="docs-palette-swatch" style={{ backgroundColor: current.color }} />
        <span>主题色</span>
        <span className="docs-palette-current">{current.label}</span>
        <svg aria-hidden="true" viewBox="0 0 20 20" className="size-4 transition-transform"><path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </summary>
      <div className="docs-palette-options" role="group" aria-label="选择文档主题色">
        {PALETTES.map((palette) => (
          <button
            key={palette.value}
            type="button"
            className="docs-palette-option"
            aria-pressed={selected === palette.value}
            onClick={(event) => {
              selectPalette(palette.value);
              event.currentTarget.closest('details')?.removeAttribute('open');
            }}
          >
            <span aria-hidden="true" className="docs-palette-swatch" style={{ backgroundColor: palette.color }} />
            <span>{palette.label}</span>
            {selected === palette.value && <span className="ms-auto text-fd-primary" aria-hidden="true">✓</span>}
          </button>
        ))}
      </div>
    </details>
  );
}
