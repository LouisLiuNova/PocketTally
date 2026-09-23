import Link from 'next/link';

const routes = {
  user: '/docs/user/',
  developer: '/docs/developer/',
};

export default function HomePage() {
  return (
    <main className="docs-home min-h-screen">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <header className="flex items-center justify-between border-b border-fd-border/70 py-5">
          <Link href="/" className="inline-flex items-center gap-3 rounded-md text-lg font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-fd-primary">
            <span aria-hidden="true" className="flex size-8 items-center justify-center rounded-lg bg-fd-primary text-sm font-bold text-fd-primary-foreground">P</span>
            PocketTally <span className="font-normal text-fd-muted-foreground">/ 文档</span>
          </Link>
          <a className="rounded-md px-2 py-1 text-sm text-fd-muted-foreground hover:text-fd-foreground focus-visible:outline-2 focus-visible:outline-fd-primary" href="https://github.com/LouisLiuNova/PocketTally">GitHub ↗</a>
        </header>

        <section className="grid items-center gap-12 py-16 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-16 lg:py-24">
          <div>
            <p className="mb-5 inline-flex items-center rounded-full border border-fd-border bg-fd-background/80 px-3 py-1 text-xs font-medium text-fd-muted-foreground">v0.2.0 发布预览 · 当前公开版 v0.1.0</p>
            <h1 className="max-w-xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl lg:text-6xl">你的钱，<br /><span className="text-fd-primary">清清楚楚。</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-fd-muted-foreground">轻量、私有的个人记账应用。记录每笔收支，核对账户余额，清晰了解钱花在了哪里。</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link className="rounded-lg bg-fd-primary px-5 py-3 font-medium text-fd-primary-foreground shadow-sm transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary" href={routes.user}>开始使用 →</Link>
              <Link className="rounded-lg border border-fd-border bg-fd-background/85 px-5 py-3 font-medium transition hover:bg-fd-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary" href={routes.developer}>开发者文档</Link>
            </div>
          </div>
          <figure className="overflow-hidden rounded-2xl border border-fd-border bg-fd-card p-2 shadow-xl shadow-black/10 dark:shadow-black/30">
            <img className="w-full rounded-xl" src="/PocketTally/overview-ruri.png" alt="PocketTally 总览页面：账户余额、现金流和支出分类" width="1440" height="1000" />
            <figcaption className="px-2 pb-1 pt-3 text-xs text-fd-muted-foreground">产品界面 · 演示账本数据</figcaption>
          </figure>
        </section>

        <section className="pb-20" aria-labelledby="choose-guide">
          <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="mb-2 text-sm font-medium text-fd-primary">按任务阅读</p>
              <h2 id="choose-guide" className="text-2xl font-semibold tracking-tight sm:text-3xl">找到适合你的指南</h2>
            </div>
            <Link href="/docs/" className="text-sm text-fd-muted-foreground underline-offset-4 hover:underline">查看文档总览 →</Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Link href={routes.user} className="group rounded-2xl border border-fd-border bg-fd-card/90 p-7 transition hover:border-fd-primary hover:shadow-md focus-visible:outline-2 focus-visible:outline-fd-primary">
              <span aria-hidden="true" className="mb-6 flex size-10 items-center justify-center rounded-xl bg-fd-accent text-xl">◫</span>
              <h3 className="text-xl font-semibold">用户文档 <span className="float-right text-fd-muted-foreground group-hover:text-fd-primary">↗</span></h3>
              <p className="mt-3 leading-7 text-fd-muted-foreground">从创建账户和第一笔交易开始，学习日常记账、查询统计、纠错与退款。</p>
            </Link>
            <Link href={routes.developer} className="group rounded-2xl border border-fd-border bg-fd-card/90 p-7 transition hover:border-fd-primary hover:shadow-md focus-visible:outline-2 focus-visible:outline-fd-primary">
              <span aria-hidden="true" className="mb-6 flex size-10 items-center justify-center rounded-xl bg-fd-accent text-xl">⌘</span>
              <h3 className="text-xl font-semibold">开发者文档 <span className="float-right text-fd-muted-foreground group-hover:text-fd-primary">↗</span></h3>
              <p className="mt-3 leading-7 text-fd-muted-foreground">查阅部署与备份、认证恢复、参与开发、测试流程和接口契约。</p>
            </Link>
          </div>
        </section>
        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-fd-border py-8 text-sm text-fd-muted-foreground">
          <span>© PocketTally · MIT License</span>
          <Link className="underline-offset-4 hover:underline" href="/releases/v0.1.0/">查看当前公开版 v0.1.0 的发行说明 →</Link>
        </footer>
      </div>
    </main>
  );
}
