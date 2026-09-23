import Link from 'next/link';

const routes = {
  user: '/docs/user/',
  developer: '/docs/developer/',
};

export default function HomePage() {
  return (
    <main className="docs-home min-h-screen">
      <div className="docs-home-shell mx-auto px-5 sm:px-8">
        <header className="flex items-center justify-between border-b border-fd-border/70 py-5">
          <Link href="/" className="inline-flex items-center gap-3 rounded-md text-lg font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-fd-primary">
            <span aria-hidden="true" className="flex size-9 items-center justify-center rounded-xl bg-fd-primary text-sm font-bold text-fd-primary-foreground shadow-sm">P</span>
            PocketTally <span className="font-normal text-fd-muted-foreground">/ 文档</span>
          </Link>
          <a className="rounded-md px-3 py-2 text-sm font-medium text-fd-muted-foreground transition hover:bg-fd-accent hover:text-fd-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary" href="https://github.com/LouisLiuNova/PocketTally">GitHub <span aria-hidden="true">↗</span></a>
        </header>

        <section className="docs-home-hero grid items-center gap-12 py-14 sm:py-18 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-16 lg:py-24">
          <div className="relative">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-fd-primary/20 bg-fd-card/80 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-fd-primary shadow-sm">
              <span aria-hidden="true" className="size-1.5 rounded-full bg-fd-primary" />
              v0.2.0 发布预览 <span className="text-fd-border">/</span> 当前公开版 v0.1.0
            </p>
            <h1 className="max-w-xl text-4xl font-semibold leading-[1.12] tracking-tight sm:text-5xl lg:text-[3.65rem]">你的钱，<br /><span className="text-fd-primary">清清楚楚。</span></h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-fd-muted-foreground">轻量、私有的个人记账应用。记录每笔收支，核对账户余额，清晰了解钱花在了哪里。</p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link className="rounded-xl bg-fd-primary px-5 py-3 font-semibold text-fd-primary-foreground shadow-md shadow-fd-primary/15 transition hover:-translate-y-0.5 hover:shadow-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary" href={routes.user}>开始使用 <span aria-hidden="true">→</span></Link>
              <Link className="rounded-xl border border-fd-border bg-fd-card/85 px-5 py-3 font-semibold transition hover:border-fd-primary/40 hover:bg-fd-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary" href={routes.developer}>开发者文档</Link>
            </div>
            <div className="mt-9 flex flex-wrap gap-x-6 gap-y-2 text-sm text-fd-muted-foreground" aria-label="产品特点">
              <span className="inline-flex items-center gap-2"><span aria-hidden="true" className="text-fd-primary">✓</span>本地部署</span>
              <span className="inline-flex items-center gap-2"><span aria-hidden="true" className="text-fd-primary">✓</span>数据自持</span>
              <span className="inline-flex items-center gap-2"><span aria-hidden="true" className="text-fd-primary">✓</span>开源免费</span>
            </div>
          </div>
          <figure className="docs-home-screenshot overflow-hidden rounded-2xl border border-fd-border/80 bg-fd-card/90 p-2.5 sm:rounded-3xl sm:p-3">
            <img className="w-full rounded-xl border border-fd-border/70 sm:rounded-2xl" src="/PocketTally/overview-ruri.png" alt="PocketTally 总览页面：账户余额、现金流和支出分类" width="1440" height="1000" />
            <figcaption className="flex items-center justify-between gap-3 px-2 pb-1 pt-3 text-xs text-fd-muted-foreground"><span>产品界面 · 演示账本数据</span><span className="rounded-full bg-fd-accent px-2 py-1 text-fd-accent-foreground">总览</span></figcaption>
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
            <Link href={routes.user} className="docs-home-card group rounded-2xl border border-fd-border bg-fd-card/90 p-6 transition hover:border-fd-primary/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary sm:p-7">
              <div className="mb-7 flex items-center justify-between">
                <span aria-hidden="true" className="flex size-11 items-center justify-center rounded-xl bg-fd-accent text-lg font-semibold text-fd-primary">01</span>
                <span className="text-sm text-fd-muted-foreground transition group-hover:translate-x-1 group-hover:text-fd-primary" aria-hidden="true">↗</span>
              </div>
              <h3 className="text-xl font-semibold tracking-tight">用户文档</h3>
              <p className="mt-3 leading-7 text-fd-muted-foreground">从创建账户和第一笔交易开始，学习日常记账、查询统计、纠错与退款。</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-fd-primary">查看用户指南 <span aria-hidden="true">→</span></span>
            </Link>
            <Link href={routes.developer} className="docs-home-card group rounded-2xl border border-fd-border bg-fd-card/90 p-6 transition hover:border-fd-primary/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fd-primary sm:p-7">
              <div className="mb-7 flex items-center justify-between">
                <span aria-hidden="true" className="flex size-11 items-center justify-center rounded-xl bg-fd-accent text-lg font-semibold text-fd-primary">02</span>
                <span className="text-sm text-fd-muted-foreground transition group-hover:translate-x-1 group-hover:text-fd-primary" aria-hidden="true">↗</span>
              </div>
              <h3 className="text-xl font-semibold tracking-tight">开发者文档</h3>
              <p className="mt-3 leading-7 text-fd-muted-foreground">查阅部署与备份、认证恢复、参与开发、测试流程和接口契约。</p>
              <span className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-fd-primary">浏览技术文档 <span aria-hidden="true">→</span></span>
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
