# 通用前端测试方案与指示

## 1. 文档目的

本文是 PocketTally 的通用前端测试方案和执行指示，记录前端基础检查、真实后端 E2E、键盘与无障碍验收、桌面兼容性矩阵、失败排查和交付判定标准。Issue #17 与 #20 的 Chromium 验收共同组成当前方案的完整示例。

本 Issue 的浏览器范围已经收缩为 Chromium 单浏览器，阻断视口为 1280、1440 和 1920 三档桌面宽度。Firefox、WebKit 和移动端专用矩阵不属于本 Issue 的验收范围。

## 2. 验收范围

### 2.1 浏览器和视口

| 项目 | 设置 |
| --- | --- |
| 浏览器 | Playwright Chromium |
| 视口一 | 1280 × 900，亮色主题 |
| 视口二 | 1440 × 900，暗色主题 |
| 视口三 | 1920 × 900，默认主题 |
| 并发 | 1 个 worker，依次执行 |
| 阻断级别 | 三档视口全部必须通过 |

### 2.2 页面和状态

覆盖以下六个主页面及其稳定 URL：

- 总览 `/`
- 交易 `/transactions`
- 账户 `/accounts`
- 分类与标签 `/categories`
- 统计分析 `/statistics`
- 设置 `/settings`

覆盖以下数据和交互状态：

- 宽屏侧栏展开、折叠、调整宽度，以及窄屏 Slideover 导航；
- 当前路由对应的导航选中态、页面标题和 Breadcrumb；
- 折叠导航和账本状态指示器的可访问名称与 Tooltip；
- 空账本和空状态提示；
- 常规账本数据；
- 长账户名称、分类名称、交易说明和标签名称；
- 超过 20 笔交易的服务端分页；
- 近 12 个月和按月统计时间桶；
- 交易详情、交易编辑和退款编辑；
- 资源编辑、账户删除确认和交易作废确认；
- 保存失败后的错误提示与表单输入保留；
- 亮色和暗色主题切换，以及八套配色组成的 16 个正式视觉组合。

## 3. 测试环境

运行前确认以下工具和依赖可用：

```text
Bun 1.3.13
uv 0.9.18
frontend/node_modules
@playwright/test
Playwright Chromium
```

Playwright E2E 会自动启动：

```text
后端：127.0.0.1:8012
前端：127.0.0.1:3012
```

测试后端使用独立 SQLite 文件，默认路径为：

```text
frontend/.data/e2e-<进程号>.sqlite3
```

也可以在需要固定测试数据时指定：

```bash
POCKET_TALLY_E2E_DATABASE_PATH=../frontend/.data/e2e-local.sqlite3
```

不要将个人账本数据库作为 E2E 数据库使用。

## 4. 标准执行流程

### 4.1 安装 Chromium

首次执行或 Playwright 浏览器缓存失效时运行：

```bash
cd frontend
bun --bun playwright install chromium
```

Linux 环境还需要满足 Chromium 的系统依赖要求。

### 4.2 前端基础检查

```bash
cd frontend
bun run typecheck
bun run test
bun run build
```

这一步用于确认类型、前端单元逻辑和生产构建没有基础问题。

### 4.3 执行完整 Chromium 矩阵

```bash
cd frontend
bun run test:e2e:matrix
```

该命令等价于依次运行：

```bash
bun run test:e2e \
  --project=chromium-1280 \
  --project=chromium-1440 \
  --project=chromium-1920
```

当前配置保留失败截图和 trace。Nuxt 首次构建较慢，E2E 前端服务等待上限为 180 秒，后端等待上限为 120 秒。

### 4.4 仓库级检查

```bash
cd backend
uv run pytest -q
uvx ruff check .
uv run --group docs python ../scripts/docs.py check

cd ..
git diff --check
```

## 5. 测试流程和断言

### 5.1 空账本和主页面

1. 打开总览页，确认主要操作按钮可用。
2. 依次进入总览、交易、账户、分类与标签、统计分析、设置。
3. 每个页面确认 `document.documentElement.scrollWidth` 不超过视口宽度。
4. 确认页面主体可见，空账本时显示空状态提示。
5. 进入设置页，切换亮色和暗色主题；确认侧栏下方的图标滑动开关同步更新。
6. 执行 `theme.spec.ts`，检查八套配色、亮暗 token、对比度、偏好恢复、首屏属性和顶栏入口移除。
7. 检查页面没有未处理的 JavaScript 错误。

### 5.2 常规数据和长文本

测试 fixture 通过真实 API 创建两个账户、收入和支出分类、一个标签，以及包含调账、收入、支出、退款、转账和 21 笔分页交易的数据集。

随后执行：

1. 打开交易页，确认服务端总数可见并且分页按钮可用。
2. 进入下一页，确认页码发生变化且列表仍然可读。
3. 搜索带有长说明的交易并打开详情。
4. 打开交易编辑器、退款编辑器和作废确认弹窗。
5. 检查每个弹窗可见、尺寸有效，且完整位于当前视口内。
6. 打开账户页，检查账户删除确认弹窗。
7. 打开新建账户表单，模拟保存失败，确认错误提示出现且名称输入仍然保留。
8. 打开分类与标签页，确认长分类名称可见且没有横向溢出。
9. 打开统计分析，切换近 12 个月和按月粒度，确认趋势图、分类统计和下钻面板可见。

### 5.3 通用布局检查

所有目标页面和弹窗执行以下检查：

- 页面没有横向滚动溢出；
- 关键控件可见且具有可测量尺寸；
- 弹窗左右和上下边界不超出视口；
- 交易列表、筛选栏和分页仍可读；
- 统计图表、日历、分类树和下钻区域仍可读；
- 页面没有未处理的 `pageerror`；
- 保存请求失败后，用户已填写的输入内容没有丢失。

### 5.4 Issue #31 路由与深链接验收

`routing.spec.ts` 验证六个页面可直接打开和刷新，并要求页面标题、导航选中态和
`aria-current` 与当前路由一致。交易页和统计页还需覆盖：

1. 交易的搜索、页码、日期、类型、账户、分类、标签和状态筛选可从 URL 恢复；
2. 统计的时间预设、自定义范围、粒度、日历月份和父分类筛选可从 URL 恢复；
3. 默认值不写入 URL，非法、未知或重复参数通过 `replace` 自动规范化；
4. 下拉、日期和分页形成可前进/后退的历史，搜索防抖更新且不为每个字符建立历史；
5. 交易日期使用空 query 值表达显式无边界，自定义统计范围无效时不发起请求；
6. 总览独占首次使用引导，统计页使用“当前筛选范围暂无可分析数据”的专属空状态；
7. 访问交易页不请求统计接口，避免无关接口失败阻断当前页面。

聚焦执行：

```bash
cd frontend
bun run test:e2e --project=chromium-1280 routing.spec.ts
```

### 5.5 Issue #30 应用壳层验收

`app-shell.spec.ts` 使用真实路由和响应式视口验证：

1. 宽屏侧栏可折叠和展开，折叠后六个导航入口仍有可访问名称；
2. 页面标题、Breadcrumb、`aria-current` 和 URL 保持一致；
3. 账本、CNY 和 Asia/Shanghai 状态在折叠后只显示图标，仍可聚焦并通过 Tooltip 读取完整语义；
4. 680 像素窄屏隐藏桌面侧栏，使用具名按钮打开 Slideover；
5. Slideover 中切换路由后自动关闭，页面无横向溢出；
6. 打开 Slideover 时执行 axe 扫描，critical/serious 问题数必须为 0。

聚焦执行：

```bash
cd frontend
bun run test:e2e --project=chromium-1280 app-shell.spec.ts
```

### 5.6 Issue #17 键盘与无障碍验收

新增的 `keyboard-accessibility.spec.ts` 不使用鼠标点击完成主流程，使用键盘完成以下路径：

1. 创建账户和支出分类；
2. 通过调账创建余额，再记录支出；
3. 打开交易详情、创建退款并作废退款；
4. 使用交易状态筛选，并进入统计分类下钻；
5. 验证表单弹窗打开后焦点进入弹窗，连续 `Tab` 不离开弹窗，`Escape` 关闭后焦点恢复到触发控件；
6. 模拟网络失败，确认 `role="alert"` 出现且输入保留；在请求未完成时重复按 `Enter`，确认只发送一次写入；
7. 使用分类用途 Tab 的左右方向键切换；
8. 使用 axe 检查主页面和交易表单弹窗，critical/serious 问题数必须为 0。

测试入口：

```bash
cd frontend
bun run test:e2e --project=chromium-1280 keyboard-accessibility.spec.ts
```

## 6. 单视口调试

遇到矩阵失败时，先单独运行失败的项目：

```bash
cd frontend
bun run test:e2e --project=chromium-1280
bun run test:e2e --project=chromium-1440
bun run test:e2e --project=chromium-1920
```

只运行新增兼容性测试：

```bash
bun run test:e2e --project=chromium-1280 desktop-compatibility.spec.ts
```

失败产物位于：

```text
frontend/test-results/
```

其中包括失败截图、错误上下文和 trace。查看 trace 时，在 `frontend` 目录运行：

```bash
bunx playwright show-trace test-results/<失败目录>/trace.zip
```

如果出现端口占用，先确认是否仍有测试残留进程，再只清理占用 8012 或 3012 的测试服务。不要停止个人账本服务或删除默认账本数据库。

## 7. 通过标准

Issue #17/#20 只有在以下条件全部满足时才算通过：

1. Chromium 1280、1440、1920 三档矩阵全部通过。
2. 六个主页面没有横向溢出、关键控件遮挡或不可操作问题。
3. 空状态、常规数据、长文本、20 笔以上分页和多时间桶统计均通过。
4. 详情、编辑、退款、作废确认和删除确认弹窗均完整位于视口内。
5. 至少一档验证亮色主题，至少一档验证暗色主题。
6. 保存失败后表单输入内容仍然保留。
7. `bun run test:e2e:matrix` 可以作为完整 Chromium 验收命令重复执行。
8. 纯键盘主流程、弹窗焦点、重复提交和 axe critical/serious 扫描全部通过。
9. 前端类型检查、单元测试、生产构建、E2E、后端测试、Ruff、文档检查和 `git diff --check` 全部通过。
10. 六个路由可直接访问和刷新，交易与统计 query 可规范化并通过浏览器历史恢复。
11. 宽屏折叠侧栏、Breadcrumb、紧凑状态指示器和窄屏 Slideover 导航通过 `app-shell.spec.ts` 验收。

## 8. 当前验证记录

2026-09-10 Issue #31 本地验证结果：

- 路由聚焦验收：4/4 通过；
- Chromium 1280、1440、1920 完整矩阵：45/45 通过；
- 前端单元测试：15/15 通过；
- 前端类型检查与生产构建：通过；
- 后端测试与 Ruff：通过；
- 文档契约检查与构建、Compose 配置检查、`git diff --check`：通过；
- 六个路由直达、刷新、标题及导航选中态，query 规范化、显式无边界、前进后退恢复、统计专属空状态和按页请求边界：通过。

2026-09-09 Issue #17 本地验证结果：

- Chromium 矩阵：24/24 通过；其中键盘与无障碍 spec 为 9/9 通过；
- 前端单元测试：5 passed；
- 前端类型检查：通过；
- 前端生产构建：通过；
- axe critical/serious 扫描：0 violations；
- 纯键盘记账、退款、作废、筛选、统计下钻：通过；
- 弹窗焦点约束与恢复、Tab/方向键、失败保留输入和重复提交：通过。

2026-09-08 本地验证结果：

- Chromium 矩阵：15/15 通过；
- 前端单元测试：5 passed；
- 前端类型检查：通过；
- 前端生产构建：通过；
- 后端测试：通过；
- Ruff：通过；
- 文档契约检查：通过；
- `git diff --check`：通过。

本记录只证明当前代码和本地环境下的 Chromium 桌面验收结果，不扩大 Firefox、WebKit、移动端或 CI 的支持承诺。
