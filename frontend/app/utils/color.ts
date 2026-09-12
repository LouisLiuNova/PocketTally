const HEX_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/

export function isValidHexColor(value: string): boolean {
  return HEX_COLOR_PATTERN.test(value)
}

export function colorValidationMessage(value: string): string {
  if (!value) return '请输入颜色值，格式为 #RRGGBB'
  if (!value.startsWith('#')) return '颜色值必须以 # 开头'
  if (value.length !== 7) return '颜色值必须是 6 位十六进制颜色（#RRGGBB）'
  return '颜色值只能包含十六进制字符（0-9、A-F）'
}
