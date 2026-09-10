# 前端语义主题与配色契约

本文记录 Issue #27 建立的 PocketTally 颜色契约。后续设置页、应用壳层、消息系统和业务页面必须消费这里定义的语义角色，不在组件内另建品牌色体系。

## 支持范围

PocketTally 支持亮色、暗色和跟随系统三种偏好。跟随系统只决定实际使用亮色或暗色，不形成第三套颜色。八套配色与两种实际模式组成 16 个正式支持的视觉组合。

| 配色 | 标识 | 种子色 | 视觉定位 |
| --- | --- | --- | --- |
| 瑠璃浅葱 | `ruri` | `#005CAF` | 清晰、可靠的默认蓝 |
| 朱鷺色 | `toki` | `#C73E3A` | 柔和、温暖的红 |
| 松葉色 | `matsuba` | `#42602D` | 稳定、自然的绿 |
| 藤紫 | `fuji` | `#6F5C9A` | 柔和、个性的紫 |
| 山吹 | `yamabuki` | `#FFA400` | 明快、积极的金黄 |
| 浅葱 | `asagi` | `#48929B` | 清爽、冷静的青蓝 |
| 紺桔梗 | `konkikyo` | `#191F45` | 克制、专业的靛蓝 |
| 胡桃 | `kurumi` | `#A86F4C` | 自然、沉稳的暖棕 |

种子色用于配色身份、设置页预览和静态色阶生成，不直接承担文字、按钮或焦点角色。每套配色在 `frontend/app/assets/css/theme.css` 中提供明确的 `brand-50` 至 `brand-950` 色阶；运行时只切换静态 token，不动态生成颜色。

## Token 分层

### Nuxt UI 基础角色

组件优先使用 Nuxt UI 的语义能力：

- `primary`：当前页面唯一的主要操作；
- `neutral`：次要、轮廓和幽灵操作；
- `success`、`info`、`warning`、`error`：跨配色保持固定含义的状态；
- `--ui-text-*`：文字层级；
- `--ui-bg-*`：页面、卡片、浮层和强调表面；
- `--ui-border-*`：普通、弱化、强调和反色边界。

`app.config.ts` 将 `primary` 指向自有 `brand` 色阶。禁止再将固定的 Tailwind `emerald` 或某个十六进制颜色当作全局主色。

### PocketTally 补充角色

- `--pt-on-primary`：实色主要操作上的文字和图标；
- `--pt-primary-container` / `--pt-on-primary-container`：选中态、强调卡和弱强调区域；
- `--pt-focus-ring`：键盘焦点；
- `--pt-surface-page` / `--pt-surface-card` / `--pt-surface-inverted`：页面、卡片和反色导航表面；
- `--pt-chart-income`、`--pt-chart-expense`、`--pt-chart-refund`、`--pt-chart-transfer`：固定账务语义；
- `--pt-chart-category-*`、`--pt-chart-grid`、`--pt-chart-axis`：分类序列和图表基础元素。

旧页面仍使用的 `--brand`、`--ink`、`--muted`、`--line`、`--paper` 和 `--card` 是上述 token 的兼容别名，不是独立颜色来源。页面迁移到 Nuxt UI 后应优先使用正式语义角色。

## 亮色与暗色规则

亮色模式使用近白的轻染页面背景、白色卡片和较深的 Primary。选中态和强调卡使用浅色 Primary Container；侧栏使用同色相的深色反色表面。

暗色模式使用低彩度深色页面背景和逐级提亮的卡片、浮层，不使用纯黑。Primary 从同一品牌色阶选择较亮 tone，只用于按钮、焦点、链接和少量关键数据；大面积强调使用深色 Primary Container。侧栏与页面进入同一深色体系，通过边框、surface 层级和选中标记区分。

状态色和账务图表色不随品牌配色改变含义。暗色版本可以提高明度并降低使用面积，但收入、支出、退款和转账必须继续使用文字、图例、正负号或不同图形辅助表达。

## 组件用色

| 场景 | 颜色角色 | 必须同时提供的非颜色线索 |
| --- | --- | --- |
| 页面主操作 | `primary/solid` | 动作文字和可访问名称 |
| 次要操作 | `neutral/outline`、`soft` 或 `ghost` | 边界、图标或文字 |
| 危险操作 | `error` | 危险文案、图标或确认模式 |
| 导航、Tab、筛选选中 | Primary Container | 字重、图标、边缘标记或 `aria-current`/`aria-selected` |
| 指标强调卡 | Primary Container | 标题、数值和说明文字 |
| 键盘焦点 | Focus Ring | 至少 2px 可见轮廓，不以背景色变化替代 |
| 收支图表 | Chart 语义色 | 图例、标签、数值或正负号 |

用户为分类和标签保存的颜色属于账本内容，不随主题替换。展示这些颜色时必须同时显示名称、图标或数值，不能让色点独自承担含义。

## 无障碍与验收

- 普通文字与背景的对比度至少为 4.5:1；
- 大字号文字、必要图标、控件边界、焦点环和图表关键图形至少为 3:1；
- 焦点环分别在页面、卡片、侧栏、实色按钮和弹层背景上检查；
- hover、pressed、active、disabled 和错误状态不能只改变色相；
- 所有 16 个组合必须通过 token 完整性和对比度自动化验收；
- Chromium 桌面矩阵覆盖默认主题以及山吹亮色、浅葱暗色、紺桔梗暗色和胡桃亮／暗等边界组合。

## 外观偏好兼容

外观偏好继续保存在 `pockettally-appearance`：

```json
{
  "theme": "system",
  "palette": "ruri"
}
```

现有四种配色值保持不变，新配色只扩展允许值。主题和配色字段分别验证：未知主题回退到 `system`，未知配色回退到 `ruri`。首屏脚本在 hydration 前应用偏好，并同步 Nuxt UI 使用的 `.light`/`.dark` class、`data-theme`、`data-palette` 和浏览器 `color-scheme`。

## 扩展新配色

新增配色必须同时完成以下工作：

1. 在唯一的外观 registry 中增加标识、简体中文名称、种子、预览和描述；
2. 生成并提交完整的静态品牌色阶和 Light/Dark neutral surface；
3. 不改变 success、info、warning、error 和账务图表语义；
4. 补充单元测试和 16 组合之外的新组合验收；
5. 对浏览器最终计算颜色执行 WCAG 对比度检查，而不是只检查种子或生成参数。
