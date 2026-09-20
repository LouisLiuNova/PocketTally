# 认证与会话

PocketTally 的认证边界面向单个账本所有者，不提供多租户、公开注册或密码找回网页。
浏览器只持有 HttpOnly 会话 Cookie，后端在独立的 `pocket-tally-auth.sqlite3` 中保存
Argon2id 密码哈希、会话摘要和登录退避状态；账本备份不包含这个文件。

## 生产边界

- 生产环境必须设置 `POCKET_TALLY_PUBLIC_ORIGIN=https://<实际域名>`，并由 HTTPS 反向代理终止 TLS。
- FastAPI 只在 Compose 网络中暴露；反向代理将浏览器请求转发到 Nuxt 同源代理。
- 生产 Cookie 使用 `__Host-` 前缀、`Secure`、`HttpOnly`、`SameSite=Strict` 和根路径。
- 写请求同时校验精确 `Origin`/`Referer`、`Sec-Fetch-Site` 与固定 `X-PocketTally-CSRF: 1` 请求头。
- 登录失败按客户端地址持久化退避；服务端最多保留 5 个会话，空闲 30 分钟或绝对 12 小时过期。

这套边界不能替代 HTTPS、主机补丁、反向代理访问控制或宿主机磁盘加密。不要直接把
FastAPI 端口发布到公网，也不要把 `pocket-tally-auth.sqlite3` 放进应用层账本备份。

## 初始化与恢复

初次部署由宿主机管理员在后端容器执行：

```bash
docker compose run --rm backend pocket-tally-auth init --username owner
```

CLI 不输出密码，也不会在日志中记录密码。忘记密码时，先确认只有管理员可访问主机，
再执行：

```bash
docker compose run --rm backend pocket-tally-auth reset-password
```

该命令重设 Argon2id 哈希并撤销全部浏览器会话。疑似泄露时可只撤销会话：

```bash
docker compose run --rm backend pocket-tally-auth revoke-sessions
```

`status` 只输出是否已初始化和当前会话数量：

```bash
docker compose run --rm backend pocket-tally-auth status
```

## 数据与备份

`backend/db/auth-schema.sql` 和 `docs/contracts/db-auth.dbml` 是独立鉴权库的结构参考。
应用层 `backup` 工具只处理账本库；鉴权库应由宿主机备份策略单独保护，并使用加密、访问
控制严格的主机级备份。恢复账本不会改变密码或会话；恢复鉴权库也不应覆盖账本文件。

## 测试环境

纯业务单元测试可通过 `POCKET_TALLY_ENVIRONMENT=test` 默认关闭认证，以保持测试数据隔离。
端到端测试会显式启用认证、初始化临时所有者并使用真实登录 Cookie；这不代表生产可以跳过
初始化或 HTTPS 配置。
