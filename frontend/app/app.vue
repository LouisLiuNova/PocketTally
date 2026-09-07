<script setup lang="ts">
const navItems = [
  { label: '总览', icon: 'i-lucide-layout-dashboard' },
  { label: '交易', icon: 'i-lucide-arrow-left-right' },
  { label: '账户', icon: 'i-lucide-wallet-cards' },
  { label: '分类与标签', icon: 'i-lucide-shapes' },
  { label: '统计分析', icon: 'i-lucide-chart-no-axes-combined' },
]

const activeView = ref('总览')
const showComposer = ref(false)
const showDetail = ref(false)
const showSuccess = ref(false)
const transactionType = ref('支出')
const search = ref('')
const range = ref('本月')
const grain = ref('按日')
const amountExpression = ref('68.00')
const occurredAt = ref('2026-09-07T19:24')
const selectedCategory = ref('餐饮')
const selectedSubcategory = ref('午餐')
const showSubcategories = ref(false)
const showCategoryEditor = ref(false)
const newCategoryName = ref('')
const showCalculator = ref(false)
const trendMode = ref<'period' | 'cumulative'>('period')
const sourceAccount = ref('微信零钱')
const destinationAccount = ref('招商银行 · 4821')
const themeMode = ref<'light' | 'dark' | 'system'>('system')
const palette = ref('ruri')
const showAppearance = ref(false)
const calendarMonth = ref('2026-09')
let webMcpLifecycle: AbortController | undefined

const categories = computed(() => transactionType.value === '收入'
  ? [
      { name: '工资', icon: 'i-lucide-briefcase-business', color: '#2A83A2' },
      { name: '奖金', icon: 'i-lucide-sparkles', color: '#7B6BA8' },
      { name: '理财', icon: 'i-lucide-chart-no-axes-combined', color: '#2D8E7B' },
      { name: '其他', icon: 'i-lucide-ellipsis', color: '#8B918F' },
    ]
  : transactionType.value === '支出'
    ? [
        { name: '餐饮', icon: 'i-lucide-utensils', color: '#E98B2A' },
        { name: '交通', icon: 'i-lucide-train-front', color: '#2A83A2' },
        { name: '购物', icon: 'i-lucide-shopping-bag', color: '#7B6BA8' },
        { name: '居住', icon: 'i-lucide-house', color: '#2D8E7B' },
        { name: '娱乐', icon: 'i-lucide-gamepad-2', color: '#C95C68' },
        { name: '医疗', icon: 'i-lucide-cross', color: '#B4473E' },
      ]
    : [])

const amountResult = computed(() => {
  const expression = amountExpression.value.replace(/[×x]/g, '*').replace(/÷/g, '/')
  if (!/^\s*\d+(?:\.\d+)?(?:\s*[+\-*/]\s*\d+(?:\.\d+)?)*\s*$/.test(expression)) return null
  const tokens = expression.match(/\d+(?:\.\d+)?|[+\-*/]/g)
  if (!tokens) return null
  let total = Number(tokens[0])
  for (let i = 1; i < tokens.length; i += 2) {
    const value = Number(tokens[i + 1])
    if (tokens[i] === '+') total += value
    if (tokens[i] === '-') total -= value
    if (tokens[i] === '*') total *= value
    if (tokens[i] === '/') total /= value
  }
  return Number.isFinite(total) && total >= 0 ? total.toFixed(2) : null
})

const paletteOptions = [
  { id: 'ruri', label: '瑠璃浅葱', colors: ['#005CAF', '#33A6B8'] },
  { id: 'toki', label: '朱鷺色', colors: ['#C73E3A', '#F4A7B9'] },
  { id: 'matsuba', label: '松葉色', colors: ['#42602D', '#86A697'] },
  { id: 'fuji', label: '藤紫', colors: ['#6F5C9A', '#B28FCE'] },
]

const subcategories: Record<string, string[]> = {
  餐饮: ['早餐', '午餐', '晚餐', '咖啡茶饮'],
  交通: ['公交地铁', '打车', '铁路航空', '加油停车'],
  购物: ['日用', '服饰', '数码', '家居'],
  居住: ['房租', '水电燃气', '物业', '维修'],
  娱乐: ['影音', '游戏', '旅行', '运动'],
  医疗: ['药品', '门诊', '体检'],
  工资: ['基本工资', '补贴'],
  奖金: ['绩效奖金', '年终奖'],
  理财: ['利息', '分红', '投资收益'],
  其他: ['其他收入'],
}

const calendarMonthOptions = [
  { value: '2026-09', label: '2026年9月' },
  { value: '2026-08', label: '2026年8月' },
  { value: '2026-07', label: '2026年7月' },
  { value: '2026-06', label: '2026年6月' },
  { value: '2026-05', label: '2026年5月' },
  { value: '2026-04', label: '2026年4月' },
]

const calendarTitle = computed(() => calendarMonthOptions.find(item => item.value === calendarMonth.value)?.label || calendarMonth.value)
const calendarDays = computed(() => {
  const [year, month] = calendarMonth.value.split('-').map(Number)
  const firstDay = new Date(year, month - 1, 1)
  const mondayOffset = (firstDay.getDay() + 6) % 7
  const gridStart = new Date(year, month - 1, 1 - mondayOffset)
  const septemberValues: Record<number, number> = { 1: 620, 2: -128, 3: -340, 5: -96, 6: 99, 7: 18562, 8: -68, 9: -226, 11: -45, 12: -510, 14: -86, 16: -228, 18: 860, 20: -76, 22: -390, 25: -126, 28: 99, 30: -248 }
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(gridStart)
    date.setDate(gridStart.getDate() + index)
    const current = date.getMonth() === month - 1
    const value = calendarMonth.value === '2026-09' && current ? septemberValues[date.getDate()] || 0 : current && date.getDate() % 5 === 0 ? -date.getDate() * 12 : 0
    const tone = value > 1000 ? 3 : value > 0 ? 1 : value < -250 ? -2 : value < 0 ? -1 : 0
    return { key: date.toISOString(), day: date.getDate(), value, tone, current, today: calendarMonth.value === '2026-09' && date.getDate() === 7 && current }
  })
})

function chooseCategory(name: string) {
  selectedCategory.value = name
  selectedSubcategory.value = subcategories[name]?.[0] || ''
  showSubcategories.value = true
}

function pressCalculator(key: string) {
  if (key === 'C') amountExpression.value = ''
  else if (key === '⌫') amountExpression.value = amountExpression.value.slice(0, -1)
  else amountExpression.value += key
}

function confirmCalculator() {
  if (!amountResult.value) return
  amountExpression.value = amountResult.value
  showCalculator.value = false
}

function swapAccounts() {
  const current = sourceAccount.value
  sourceAccount.value = destinationAccount.value
  destinationAccount.value = current
}

function addCategory() {
  if (!newCategoryName.value.trim()) return
  selectedCategory.value = newCategoryName.value.trim()
  selectedSubcategory.value = ''
  newCategoryName.value = ''
  showCategoryEditor.value = false
}

function applyAppearance() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  document.documentElement.dataset.theme = themeMode.value === 'system' ? (prefersDark ? 'dark' : 'light') : themeMode.value
  document.documentElement.dataset.palette = palette.value
}

const pageTitle = computed(() => ({
  总览: '早上好，Louis',
  交易: '每一笔，都清清楚楚',
  账户: '账户',
  '分类与标签': '分类与标签',
  统计分析: '统计分析',
}[activeView.value] || activeView.value))

function saveTransaction() {
  showComposer.value = false
  showSuccess.value = true
  window.setTimeout(() => { showSuccess.value = false }, 2600)
}

onMounted(() => {
  applyAppearance()
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyAppearance)
  const modelContext = (document as Document & { modelContext?: { registerTool: (tool: object, options?: { signal?: AbortSignal }) => void | Promise<void> } }).modelContext
  if (!modelContext?.registerTool) return
  webMcpLifecycle = new AbortController()
  void Promise.resolve(modelContext.registerTool({
    name: 'start_transaction_creation',
    title: '开始记账',
    description: '打开 PocketTally 的记账表单，并预选收入、支出、转账或调账类型。',
    inputSchema: {
      type: 'object',
      properties: { type: { type: 'string', enum: ['支出', '收入', '转账', '调账'] } },
      required: ['type'],
      additionalProperties: false,
    },
    annotations: { readOnlyHint: false, untrustedContentHint: false },
    execute(input: unknown) {
      const value = input as { type?: string }
      if (!value.type || !['支出', '收入', '转账', '调账'].includes(value.type)) throw new Error('不支持的交易类型')
      transactionType.value = value.type
      showComposer.value = true
      return { status: 'ready', type: value.type }
    },
  }, { signal: webMcpLifecycle.signal }))
})

watch([themeMode, palette], applyAppearance)

onBeforeUnmount(() => {
  webMcpLifecycle?.abort()
  window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', applyAppearance)
})

const transactions = [
  { icon: 'i-lucide-utensils', tone: 'amber', name: '小满手工粉', meta: '餐饮 · 午餐', time: '今天 12:36', amount: '-¥38.00' },
  { icon: 'i-lucide-briefcase-business', tone: 'emerald', name: '九月工资', meta: '收入 · 工资', time: '今天 09:02', amount: '+¥18,600.00' },
  { icon: 'i-lucide-train-front', tone: 'blue', name: '地铁通勤', meta: '交通 · 公交地铁', time: '昨天 18:21', amount: '-¥6.00' },
  { icon: 'i-lucide-shopping-bag', tone: 'violet', name: '山姆会员商店', meta: '购物 · 日用', time: '9月5日 20:14', amount: '-¥326.80' },
]
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark"><UIcon name="i-lucide-circle-dollar-sign" /></div><span class="brand-label">PocketTally</span></div>
      <nav aria-label="主导航">
        <button v-for="item in navItems" :key="item.label" class="nav-item" :class="{ active: activeView === item.label }" @click="activeView = item.label">
          <UIcon :name="item.icon" /><span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>
      <div class="sidebar-foot">
        <button class="nav-item"><UIcon name="i-lucide-settings-2" /><span class="nav-label">设置</span></button>
      </div>
    </aside>

    <main>
      <header class="topbar">
        <div><p class="eyebrow">2026年9月7日 · 星期一</p><h1>{{ pageTitle }}</h1></div>
        <div class="top-actions"><UButton color="neutral" variant="ghost" icon="i-lucide-search" aria-label="搜索" /><div class="appearance-wrap"><UButton color="neutral" variant="ghost" icon="i-lucide-sun-moon" aria-label="外观设置" @click="showAppearance = !showAppearance" /><div v-if="showAppearance" class="appearance-popover"><strong>外观</strong><span>主题</span><div class="appearance-options"><button v-for="mode in [{id:'light',label:'亮色',icon:'i-lucide-sun'},{id:'dark',label:'暗色',icon:'i-lucide-moon'},{id:'system',label:'跟随系统',icon:'i-lucide-monitor'}]" :key="mode.id" :class="{active:themeMode===mode.id}" @click="themeMode=mode.id as typeof themeMode"><UIcon :name="mode.icon" />{{mode.label}}</button></div><span>日本传统色</span><div class="palette-options"><button v-for="item in paletteOptions" :key="item.id" :class="{active:palette===item.id}" @click="palette=item.id"><i><b v-for="color in item.colors" :key="color" :style="{background:color}" /></i>{{item.label}}<UIcon v-if="palette===item.id" name="i-lucide-check" /></button></div></div></div><UButton icon="i-lucide-plus" label="记一笔" @click="showComposer = true" /></div>
      </header>

      <template v-if="activeView === '总览'">
      <section class="metric-grid" aria-label="本月概览">
        <article class="metric-card feature"><div class="metric-head"><span>实际净现金流</span><span class="trend up"><UIcon name="i-lucide-trending-up" /> 22.8%</span></div><strong>+¥12,864.20</strong><p>比上月多 ¥2,388.40</p><div class="sparkline"><i v-for="h in [30,42,38,56,44,62,48,68,58,74,64,82]" :key="h" :style="{height: `${h}%`}" /></div></article>
        <article class="metric-card"><div class="metric-icon income"><UIcon name="i-lucide-arrow-down-left" /></div><span>本月收入</span><strong>¥20,860.00</strong><p class="trend up">较上月 +8.2%</p></article>
        <article class="metric-card"><div class="metric-icon expense"><UIcon name="i-lucide-arrow-up-right" /></div><span>消费净支出</span><strong>¥7,995.80</strong><p class="trend down">较上月 +3.4%</p></article>
      </section>

      <section class="dashboard-grid">
        <article class="panel cashflow-panel">
          <div class="panel-head"><div><p class="eyebrow">现金流趋势</p><h2>收支节奏</h2></div><div class="segmented"><button class="active">6个月</button><button>12个月</button></div></div>
          <div class="chart-wrap"><div class="chart-y"><span>20k</span><span>10k</span><span>0</span></div><div class="bars"><div v-for="(bar, i) in [[54,25],[68,34],[48,38],[74,29],[62,42],[82,31]]" :key="i" class="bar-group"><div class="bar income-bar" :style="{height: `${bar[0]}%`}"/><div class="bar expense-bar" :style="{height: `${bar[1]}%`}"/><span>{{ ['4月','5月','6月','7月','8月','9月'][i] }}</span></div></div></div>
          <div class="legend"><span><i class="dot income-dot"/>收入</span><span><i class="dot expense-dot"/>支出</span><span class="chart-note">退款按实际到账日计入现金流</span></div>
        </article>

        <article class="panel account-panel"><div class="panel-head"><div><p class="eyebrow">账户余额</p><h2>¥106,238.54</h2></div><button class="icon-link"><UIcon name="i-lucide-arrow-up-right" /></button></div><div class="account-list"><div><span class="account-logo wechat">微</span><p><strong>微信零钱</strong><small>日常消费</small></p><b>¥2,186.30</b></div><div><span class="account-logo bank">招</span><p><strong>招商银行</strong><small>储蓄卡 · 4821</small></p><b>¥86,452.24</b></div><div><span class="account-logo cash">¥</span><p><strong>现金</strong><small>随身现金</small></p><b>¥1,600.00</b></div></div></article>

        <article class="panel recent-panel"><div class="panel-head"><div><p class="eyebrow">最近交易</p><h2>最新动态</h2></div><button class="text-link">查看全部 <UIcon name="i-lucide-arrow-right" /></button></div><div class="transactions"><div v-for="item in transactions" :key="item.name" class="transaction"><span class="transaction-icon" :class="item.tone"><UIcon :name="item.icon" /></span><p><strong>{{ item.name }}</strong><small>{{ item.meta }}</small></p><time>{{ item.time }}</time><b :class="{positive: item.amount.startsWith('+')}">{{ item.amount }}</b></div></div></article>

        <article class="panel category-panel"><div class="panel-head"><div><p class="eyebrow">消费构成</p><h2>钱花在哪</h2></div><button class="text-link">本月 <UIcon name="i-lucide-chevron-down" /></button></div><div class="donut-row"><div class="donut"><div><strong>¥7,996</strong><span>净支出</span></div></div><div class="category-list"><div><i style="--color:#ffbe5c"/><span>餐饮</span><b>¥2,486</b><small>31%</small></div><div><i style="--color:#4ad5b7"/><span>居住</span><b>¥1,920</b><small>24%</small></div><div><i style="--color:#6d8cff"/><span>购物</span><b>¥1,520</b><small>19%</small></div><div><i style="--color:#b58cff"/><span>其他</span><b>¥2,070</b><small>26%</small></div></div></div></article>
        <article class="panel calendar-panel"><div class="panel-head"><div><p class="eyebrow">实际现金流</p><h2>{{calendarTitle}}收支日历</h2></div><div class="calendar-controls"><select v-model="calendarMonth" aria-label="选择历史年月"><option v-for="month in calendarMonthOptions" :key="month.value" :value="month.value">{{month.label}}</option></select><div class="calendar-legend"><span><i class="cash-in"/>流入</span><span><i class="cash-out"/>流出</span></div></div></div><div class="cash-calendar"><span v-for="weekday in ['一','二','三','四','五','六','日']" :key="weekday" class="weekday">周{{weekday}}</span><button v-for="item in calendarDays" :key="item.key" :class="[`tone-${item.tone}`,{today:item.today,outside:!item.current}]"><b>{{item.day}}</b><span v-if="item.value">{{item.value>0?'+':''}}¥{{Math.abs(item.value).toLocaleString()}}</span><span v-else>—</span></button></div><p class="calendar-note"><UIcon name="i-lucide-info" /> 退款在实际到账日显示；点击日期可进入当天交易明细。</p></article>
      </section>
      </template>

      <section v-else-if="activeView === '交易'" class="workspace-view">
        <div class="view-toolbar">
          <div class="search-field"><UIcon name="i-lucide-search" /><input v-model="search" placeholder="搜索说明、金额或分类" /></div>
          <button class="filter-chip active">本月 <UIcon name="i-lucide-chevron-down" /></button><button class="filter-chip">全部类型 <UIcon name="i-lucide-chevron-down" /></button><button class="filter-chip">全部账户 <UIcon name="i-lucide-chevron-down" /></button><button class="filter-chip">更多筛选 <UIcon name="i-lucide-list-filter" /></button>
        </div>
        <div class="transaction-summary"><div><span>本月收入</span><strong>¥20,860.00</strong></div><div><span>消费净支出</span><strong>¥7,995.80</strong></div><div><span>实际净现金流</span><strong class="green">+¥12,864.20</strong></div><p><UIcon name="i-lucide-info" /> 退款会回到原消费日抵减支出，在实际到账日计入现金流。</p></div>
        <article class="panel ledger-panel">
          <div class="date-group"><div class="date-head"><div><strong>今天</strong><span>9月7日 · 2笔</span></div><b>+¥18,562.00</b></div><button class="ledger-row" @click="showDetail = true"><span class="transaction-icon amber"><UIcon name="i-lucide-utensils" /></span><p><strong>小满手工粉</strong><small>餐饮 / 午餐　<span class="tag">#工作日</span></small></p><span>微信零钱</span><time>12:36</time><b>-¥38.00</b><UIcon name="i-lucide-chevron-right" /></button><button class="ledger-row" @click="showDetail = true"><span class="transaction-icon emerald"><UIcon name="i-lucide-briefcase-business" /></span><p><strong>九月工资</strong><small>收入 / 工资</small></p><span>招商银行</span><time>09:02</time><b class="positive">+¥18,600.00</b><UIcon name="i-lucide-chevron-right" /></button></div>
          <div class="date-group"><div class="date-head"><div><strong>昨天</strong><span>9月6日 · 3笔</span></div><b>-¥112.50</b></div><button class="ledger-row"><span class="transaction-icon blue"><UIcon name="i-lucide-train-front" /></span><p><strong>地铁通勤</strong><small>交通 / 公交地铁　<span class="tag">#通勤</span></small></p><span>交通卡</span><time>18:21</time><b>-¥6.00</b><UIcon name="i-lucide-chevron-right" /></button><button class="ledger-row refund-row"><span class="transaction-icon refund"><UIcon name="i-lucide-rotate-ccw" /></span><p><strong>耳机退款到账</strong><small>原支出：数码配件 · 8月28日</small></p><span>招商银行</span><time>15:08</time><b class="positive">+¥99.00</b><UIcon name="i-lucide-chevron-right" /></button></div>
        </article>
      </section>

      <section v-else-if="activeView === '账户'" class="workspace-view">
        <div class="section-intro"><div><p>4 个账户</p><h2>总余额 ¥106,238.54</h2></div><UButton icon="i-lucide-plus" label="新建账户" /></div>
        <div class="account-card-grid"><article class="balance-card primary-account"><span>主要账户</span><div class="card-brand">招商银行 <UIcon name="i-lucide-landmark" /></div><strong>¥86,452.24</strong><small>储蓄卡 · 尾号 4821</small><div><button>查看流水</button><button @click="showComposer = true">余额调整</button></div></article><article class="balance-card"><span>日常消费</span><div class="card-brand">微信零钱 <b class="wechat-mini">微</b></div><strong>¥2,186.30</strong><small>借记账户</small><div><button>查看流水</button><button @click="showComposer = true">余额调整</button></div></article><article class="balance-card"><span>随身</span><div class="card-brand">现金 <UIcon name="i-lucide-banknote" /></div><strong>¥1,600.00</strong><small>借记账户</small><div><button>查看流水</button><button @click="showComposer = true">余额调整</button></div></article></div>
        <div class="info-strip"><UIcon name="i-lucide-shield-check" /><div><strong>余额由有效交易自动计算</strong><span>如实际余额不一致，请创建一笔余额调整。账户余额不会被直接改写。</span></div></div>
      </section>

      <section v-else-if="activeView === '分类与标签'" class="workspace-view">
        <div class="subtabs"><button class="active">支出分类</button><button>收入分类</button><button>标签</button></div>
        <div class="taxonomy-grid"><article class="panel tree-panel"><div class="panel-head"><div><p class="eyebrow">分类结构</p><h2>支出分类</h2></div><UButton size="sm" variant="soft" icon="i-lucide-plus" label="新建分类" /></div><div class="tree-list"><div class="tree-parent"><span class="tree-icon amber"><UIcon name="i-lucide-utensils" /></span><strong>餐饮</strong><small>¥2,486.40</small><UIcon name="i-lucide-chevron-up" /></div><div class="tree-child active"><i/><span>午餐</span><small>12 笔 · ¥968.00</small><UIcon name="i-lucide-grip-vertical" /></div><div class="tree-child"><i/><span>晚餐</span><small>8 笔 · ¥846.40</small><UIcon name="i-lucide-grip-vertical" /></div><div class="tree-child"><i/><span>咖啡茶饮</span><small>9 笔 · ¥672.00</small><UIcon name="i-lucide-grip-vertical" /></div><div class="tree-parent"><span class="tree-icon blue"><UIcon name="i-lucide-car-front" /></span><strong>交通</strong><small>¥880.00</small><UIcon name="i-lucide-chevron-down" /></div><div class="tree-parent"><span class="tree-icon violet"><UIcon name="i-lucide-shopping-bag" /></span><strong>购物</strong><small>¥1,520.00</small><UIcon name="i-lucide-chevron-down" /></div></div></article><article class="panel editor-panel"><p class="eyebrow">分类详情</p><h2>午餐</h2><label>分类名称<input value="午餐" /></label><label>上级分类<select><option>餐饮</option></select></label><div class="preview-category"><span class="tree-icon amber"><UIcon name="i-lucide-utensils" /></span><div><strong>餐饮 / 午餐</strong><small>移动分类后，历史统计将按新结构重新归集</small></div></div><div class="editor-actions"><button class="danger">删除分类</button><UButton label="保存修改" /></div></article></div>
      </section>

      <section v-else class="workspace-view analytics-view">
        <div class="view-toolbar analytics-toolbar"><div class="period-tabs"><button v-for="period in ['本月','上月','今年','近 12 个月','自定义']" :key="period" :class="{active: range === period}" @click="range = period">{{ period }}</button></div><select v-model="grain" class="filter-select" aria-label="统计粒度"><option>按日</option><option>按周</option><option>按月</option></select></div>
        <section class="stats-strip"><div><span>期间收入</span><strong>¥20,860</strong><small class="up">↑ 8.2%</small></div><div><span>消费净支出</span><strong>¥7,996</strong><small class="down">↑ 3.4%</small></div><div><span>实际净现金流</span><strong>+¥12,864</strong><small class="up">↑ ¥2,388</small></div><div class="scope-note"><UIcon name="i-lucide-calendar-clock" /><span>统计边界<br><strong>Asia/Shanghai</strong></span></div></section>
        <div class="analytics-grid"><article class="panel wide-chart"><div class="panel-head"><div><p class="eyebrow">{{ range }} · {{ grain }} · 消费净支出</p><h2>{{ trendMode === 'period' ? '支出趋势' : '累计支出' }}</h2></div><div class="segmented"><button :class="{active:trendMode==='period'}" @click="trendMode='period'">期间支出</button><button :class="{active:trendMode==='cumulative'}" @click="trendMode='cumulative'">累计支出</button></div></div><div class="line-chart"><svg viewBox="0 0 720 210" role="img" :aria-label="`${range}${grain}${trendMode==='period'?'消费净支出':'累计支出'}曲线趋势`"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--brand)" stop-opacity=".25"/><stop offset="1" stop-color="var(--brand)" stop-opacity="0"/></linearGradient></defs><path class="gridline" d="M20 40H700M20 95H700M20 150H700"/><template v-if="trendMode==='period'"><path class="area" d="M20 150 C45 142 68 130 90 125 C115 120 136 141 160 138 C187 134 207 81 230 70 C252 61 274 107 300 112 C325 116 345 99 370 98 C396 97 418 126 440 128 C464 130 486 65 510 54 C533 45 554 91 580 92 C605 93 624 78 650 82 C670 85 687 100 700 108 L700 180 L20 180Z"/><path class="line" d="M20 150 C45 142 68 130 90 125 C115 120 136 141 160 138 C187 134 207 81 230 70 C252 61 274 107 300 112 C325 116 345 99 370 98 C396 97 418 126 440 128 C464 130 486 65 510 54 C533 45 554 91 580 92 C605 93 624 78 650 82 C670 85 687 100 700 108"/></template><template v-else><path class="area" d="M20 176 C90 170 130 162 180 148 S260 125 320 112 S410 90 470 74 S560 58 610 45 S670 32 700 24 L700 180 L20 180Z"/><path class="line" d="M20 176 C90 170 130 162 180 148 S260 125 320 112 S410 90 470 74 S560 58 610 45 S670 32 700 24"/></template><g class="data-points"><circle cx="20" :cy="trendMode==='period'?150:176" r="4"/><circle cx="700" :cy="trendMode==='period'?108:24" r="4"/></g><g class="axis"><text x="20" y="202">9/1</text><text x="230" y="202">9/4</text><text x="440" y="202">9/7</text><text x="650" y="202">9/10</text></g></svg></div><p class="chart-footnote">{{ trendMode === 'period' ? '退款按原支出发生日期抵减，因此可能改变历史日期的净支出。' : '从筛选范围起点的 ¥0 开始累计。' }}</p></article><article class="panel tag-panel"><div class="panel-head"><div><p class="eyebrow">Tag 汇总</p><h2>消费场景</h2></div><UIcon name="i-lucide-tags" /></div><div class="tag-bars"><div v-for="tag in [{n:'工作日',v:'¥2,146',w:88,c:'#25ae8c'},{n:'家庭',v:'¥1,886',w:74,c:'#748cf5'},{n:'通勤',v:'¥880',w:42,c:'#ffad55'},{n:'提升',v:'¥528',w:27,c:'#a77be8'}]" :key="tag.n"><p><span><i :style="{background:tag.c}"/>{{tag.n}}</span><b>{{tag.v}}</b></p><div><i :style="{width:`${tag.w}%`,background:tag.c}"/></div></div></div><small class="tag-warning"><UIcon name="i-lucide-info" /> 同一交易可计入多个 Tag，不提供合计或占比。</small></article></div>
      </section>
    </main>

    <Transition name="fade"><div v-if="showComposer" class="modal-backdrop" @click.self="showComposer = false"><section class="composer" role="dialog" aria-modal="true" aria-label="记一笔">
      <header><div><p class="eyebrow">快速记账</p><h2>新增交易</h2></div><button aria-label="关闭" @click="showComposer = false"><UIcon name="i-lucide-x" /></button></header>
      <div class="type-switch"><button v-for="type in ['支出','收入','转账','调账']" :key="type" :class="{active: transactionType === type}" @click="transactionType = type; selectedCategory = type === '收入' ? '工资' : '餐饮'; showSubcategories=false">{{ type }}</button></div>
      <div v-if="categories.length" class="category-section">
        <div class="category-picker"><button v-for="category in categories" :key="category.name" :class="{active:selectedCategory===category.name}" @click="chooseCategory(category.name)"><span :style="{color:category.color,background:`color-mix(in srgb, ${category.color} 12%, var(--card))`,borderColor:`color-mix(in srgb, ${category.color} 35%, var(--line))`}"><UIcon :name="category.icon" /></span><small>{{category.name}}</small></button><button class="category-manage" @click="showCategoryEditor=!showCategoryEditor"><span><UIcon name="i-lucide-plus" /></span><small>管理</small></button></div>
        <Transition name="fade"><div v-if="showSubcategories" class="subcategory-popover"><div><strong>{{selectedCategory}}</strong><button aria-label="编辑分类" @click="showCategoryEditor=true"><UIcon name="i-lucide-pencil" /></button></div><button v-for="item in subcategories[selectedCategory] || []" :key="item" :class="{active:selectedSubcategory===item}" @click="selectedSubcategory=item;showSubcategories=false">{{item}}<UIcon v-if="selectedSubcategory===item" name="i-lucide-check" /></button><button class="add-subcategory" @click="showCategoryEditor=true"><UIcon name="i-lucide-plus" /> 添加二级分类</button></div></Transition>
        <Transition name="fade"><div v-if="showCategoryEditor" class="category-editor-popover"><strong>快速管理分类</strong><label>分类名称<input v-model="newCategoryName" placeholder="输入新分类名称" /></label><div><button @click="showCategoryEditor=false">取消</button><button class="primary-mini" @click="addCategory">添加并选中</button></div><small>完整层级、色号与图标可在“分类与标签”中继续编辑。</small></div></Transition>
      </div>
      <label class="amount-field"><span>金额</span><button class="amount-display" @click="showCalculator=!showCalculator"><b>¥</b><strong>{{amountResult || '0.00'}}</strong><UIcon name="i-lucide-calculator" /></button><Transition name="fade"><div v-if="showCalculator" class="calculator-popover"><div class="calculator-screen"><small>算式</small><strong>{{amountExpression || '0'}}</strong></div><div class="calculator-grid"><button v-for="key in ['C','⌫','÷','×','7','8','9','-','4','5','6','+','1','2','3','.','0','00']" :key="key" :class="{operator:['C','⌫','÷','×','-','+'].includes(key)}" @click="pressCalculator(key)">{{key}}</button><button class="calculator-confirm" :disabled="!amountResult" @click="confirmCalculator">完成</button></div></div></Transition></label>
      <template v-if="transactionType==='转账'">
        <div class="transfer-fields"><label>转出账户<select v-model="sourceAccount"><option>微信零钱</option><option>招商银行 · 4821</option><option>现金</option></select></label><button aria-label="交换转入转出账户" @click="swapAccounts"><UIcon name="i-lucide-arrow-down-up" /></button><label>转入账户<select v-model="destinationAccount"><option>招商银行 · 4821</option><option>微信零钱</option><option>现金</option></select></label></div><p class="transfer-note" :class="{error:sourceAccount===destinationAccount}"><UIcon :name="sourceAccount===destinationAccount?'i-lucide-circle-alert':'i-lucide-circle-check'" /> {{sourceAccount===destinationAccount?'转入和转出账户不能相同':'仅改变账户间资金分布，不计入收入或支出。'}}</p>
      </template>
      <template v-else-if="transactionType==='调账'"><div class="form-grid"><label>调整账户<select><option>微信零钱</option><option>招商银行 · 4821</option></select></label><label>调整方向<select><option>增加余额</option><option>减少余额</option></select></label></div><p class="transfer-note"><UIcon name="i-lucide-info" /> 调账不计入收支、分类或 Tag 统计。</p></template>
      <div v-else class="single-account"><label>{{transactionType==='收入'?'入账账户':'支付账户'}}<select><option>微信零钱</option><option>招商银行 · 4821</option></select></label><div class="category-path"><span>分类</span><strong>{{selectedCategory}}<template v-if="selectedSubcategory"> / {{selectedSubcategory}}</template></strong></div></div>
      <label>说明<input :value="transactionType==='转账'?'账户间转账':'晚餐'" /></label><label v-if="transactionType!=='调账'">Tag<div class="tag-picker"><button class="selected">工作日 <UIcon name="i-lucide-check" /></button><button>家庭</button><button>朋友聚会</button><button><UIcon name="i-lucide-plus" /></button></div></label>
      <div class="composer-actions"><label class="datetime-field"><UIcon name="i-lucide-calendar-clock" /><input v-model="occurredAt" type="datetime-local" aria-label="交易发生时间" /></label><UButton size="lg" label="保存交易" :disabled="!amountResult || (transactionType==='转账' && sourceAccount===destinationAccount)" @click="saveTransaction" /></div>
    </section></div></Transition>
    <Transition name="fade"><aside v-if="showDetail" class="detail-drawer"><header><div><p class="eyebrow">交易详情</p><h2>小满手工粉</h2></div><button @click="showDetail = false"><UIcon name="i-lucide-x" /></button></header><div class="detail-amount">-¥38.00<span class="status-dot">已入账</span></div><dl><div><dt>类型</dt><dd>支出</dd></div><div><dt>账户</dt><dd>微信零钱</dd></div><div><dt>分类</dt><dd>餐饮 / 午餐</dd></div><div><dt>发生时间</dt><dd>2026-09-07 12:36</dd></div><div><dt>Tag</dt><dd><span class="tag">#工作日</span></dd></div></dl><div class="refund-box"><div><UIcon name="i-lucide-rotate-ccw" /><span><strong>退款</strong><small>已退 ¥0.00 · 剩余可退 ¥38.00</small></span></div><button>发起退款</button></div><div class="drawer-actions"><button class="danger"><UIcon name="i-lucide-ban" /> 作废交易</button><UButton variant="soft" icon="i-lucide-pencil" label="编辑说明与 Tag" /></div></aside></Transition>
    <Transition name="toast"><div v-if="showSuccess" class="success-toast"><UIcon name="i-lucide-circle-check" /><div><strong>交易已保存</strong><span>余额与统计已重新读取</span></div></div></Transition>
  </div>
</template>
