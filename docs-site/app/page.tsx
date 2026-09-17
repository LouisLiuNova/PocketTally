import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center gap-8 px-6 py-16">
      <div className="space-y-4">
        <p className="text-sm font-medium text-fd-muted-foreground">PocketTally</p>
        <h1 className="text-4xl font-semibold tracking-tight">你的钱，清清楚楚。</h1>
        <p className="max-w-2xl text-lg text-fd-muted-foreground">
          轻量、私有的个人记账应用。数据保存在你自己的 SQLite 账本中，适合在本机或可信内网使用。
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        <Link className="rounded-lg bg-fd-primary px-4 py-2 font-medium text-fd-primary-foreground" href="/docs/">
          打开文档
        </Link>
        <a className="rounded-lg border border-fd-border px-4 py-2 font-medium" href="https://github.com/LouisLiuNova/PocketTally">
          查看仓库
        </a>
      </div>
    </main>
  );
}
