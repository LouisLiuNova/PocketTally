export const APPEARANCE_STORAGE_KEY = 'pockettally-appearance'
export const COLOR_MODE_STORAGE_KEY = 'pockettally-color-mode'

export const THEME_PREFERENCES = ['system', 'light', 'dark'] as const
export type ThemePreference = typeof THEME_PREFERENCES[number]

export const PALETTE_NAMES = [
  'ruri',
  'toki',
  'matsuba',
  'fuji',
  'yamabuki',
  'asagi',
  'konkikyo',
  'kurumi',
] as const
export type PaletteName = typeof PALETTE_NAMES[number]

export interface AppearancePreference {
  theme: ThemePreference
  palette: PaletteName
}

export interface AppearancePalette {
  value: PaletteName
  label: string
  seed: string
  preview: readonly [string, string]
  description: string
}

export const DEFAULT_APPEARANCE: AppearancePreference = {
  theme: 'system',
  palette: 'ruri',
}

export const APPEARANCE_PALETTES: readonly AppearancePalette[] = [
  { value: 'ruri', label: '瑠璃浅葱', seed: '#005CAF', preview: ['#075EB1', '#D5E3FF'], description: '清晰、可靠的默认蓝' },
  { value: 'toki', label: '朱鷺色', seed: '#C73E3A', preview: ['#B02D2B', '#FFDAD6'], description: '柔和、温暖的红' },
  { value: 'matsuba', label: '松葉色', seed: '#42602D', preview: ['#3C6A1C', '#BBF293'], description: '稳定、自然的绿' },
  { value: 'fuji', label: '藤紫', seed: '#6F5C9A', preview: ['#694FA3', '#EADDFF'], description: '柔和、个性的紫' },
  { value: 'yamabuki', label: '山吹', seed: '#FFA400', preview: ['#855300', '#FFDDB7'], description: '明快、积极的金黄' },
  { value: 'asagi', label: '浅葱', seed: '#48929B', preview: ['#006972', '#8CF2FF'], description: '清爽、冷静的青蓝' },
  { value: 'konkikyo', label: '紺桔梗', seed: '#191F45', preview: ['#4B57A9', '#DEE0FF'], description: '克制、专业的靛蓝' },
  { value: 'kurumi', label: '胡桃', seed: '#A86F4C', preview: ['#96490C', '#FFDBC8'], description: '自然、沉稳的暖棕' },
] as const

const themeSet = new Set<string>(THEME_PREFERENCES)
const paletteSet = new Set<string>(PALETTE_NAMES)

export function parseAppearance(value: unknown): AppearancePreference {
  if (!value || typeof value !== 'object') return { ...DEFAULT_APPEARANCE }
  const candidate = value as Record<string, unknown>
  return {
    theme: typeof candidate.theme === 'string' && themeSet.has(candidate.theme)
      ? candidate.theme as ThemePreference
      : DEFAULT_APPEARANCE.theme,
    palette: typeof candidate.palette === 'string' && paletteSet.has(candidate.palette)
      ? candidate.palette as PaletteName
      : DEFAULT_APPEARANCE.palette,
  }
}

export function parseStoredAppearance(value: string | null): AppearancePreference {
  if (!value) return { ...DEFAULT_APPEARANCE }
  try {
    return parseAppearance(JSON.parse(value))
  } catch {
    return { ...DEFAULT_APPEARANCE }
  }
}

export const appearanceBootScript = `(() => {
  const themes = ${JSON.stringify(THEME_PREFERENCES)};
  const palettes = ${JSON.stringify(PALETTE_NAMES)};
  let theme = 'system';
  let palette = 'ruri';
  try {
    const saved = JSON.parse(localStorage.getItem('${APPEARANCE_STORAGE_KEY}') || '{}');
    if (themes.includes(saved.theme)) theme = saved.theme;
    if (palettes.includes(saved.palette)) palette = saved.palette;
    localStorage.setItem('${COLOR_MODE_STORAGE_KEY}', theme);
  } catch {}
  const resolved = theme === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme;
  const root = document.documentElement;
  root.dataset.theme = resolved;
  root.dataset.palette = palette;
  root.style.colorScheme = resolved;
  root.classList.remove('light', 'dark');
  root.classList.add(resolved);
})();`
