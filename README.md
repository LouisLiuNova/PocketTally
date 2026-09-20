# PocketTally

> 你的钱，清清楚楚。

PocketTally 是一款轻量、私有的个人记账应用。数据保存在你自己的 SQLite 账本中，适合在本机或可信内网使用。

## 主要功能

- 管理账户、分类和标签
- 记录收入、支出、转账、调账与退款
- 搜索和筛选交易，查看多维度收支统计
- 创建、校验和恢复账本备份

> [!IMPORTANT]
> 当前主线已启用单所有者登录。生产环境仍必须通过 HTTPS 反向代理发布，并配置
> `POCKET_TALLY_PUBLIC_ORIGIN`；登录凭据和会话存放在独立的鉴权 SQLite 文件中。

## 快速开始

需要预先安装 [Docker](https://docs.docker.com/get-docker/)。在项目目录运行：

```bash
cp .env.example .env
mkdir -p data backups
docker compose pull frontend backend
docker compose up -d --no-build
```

首次启动后，在后端容器中初始化唯一所有者（命令只会在鉴权库为空时成功）：

```bash
docker compose run --rm backend pocket-tally-auth init --username owner
```

认证边界、恢复命令和生产反向代理要求见[认证与会话](docs/authentication.md)及[部署指南](https://louisliunova.github.io/PocketTally/deployment/)。

然后访问 `http://localhost:54425`。

首次使用建议依次完成：

1. 创建账户
2. 通过调账录入当前余额
3. 直接使用内置的常用收入和支出分类开始记账
4. 按个人习惯调整、删除或新增分类

在保存真实数据前，请先按照[部署指南](https://louisliunova.github.io/PocketTally/deployment/)创建并校验备份。

## 文档

- [完整文档](https://louisliunova.github.io/PocketTally/)：使用边界、业务规则和技术参考
- [部署与备份](https://louisliunova.github.io/PocketTally/deployment/)：内网部署、升级、备份和恢复
- [发行说明](https://louisliunova.github.io/PocketTally/releases/v0.1.0/)：版本能力与已知限制
- [参与开发](https://louisliunova.github.io/PocketTally/development/)：本地开发、测试和文档维护

## 许可

PocketTally 使用 [MIT License](LICENSE)。
