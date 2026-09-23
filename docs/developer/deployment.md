# 部署与备份

> [!IMPORTANT]
> 本页是 **v0.2.0 发布前预览**，说明当前主线源码构建的单所有者部署边界。v0.2.0 镜像尚未发布，不能从本页推断固定版本镜像已经可用。现行 v0.1.0 镜像无登录功能，只能在本机或可信内网使用；其完整操作见[历史部署指南](../deployment.md)。

PocketTally 使用 Docker Compose 运行前端、后端与按需备份工具。生产环境必须由 HTTPS 反向代理提供唯一公开入口，后端只在 Compose 网络中访问。部署前准备 Docker Compose、持久化的数据与备份目录、受保护的域名和独立备份存储。

## 当前主线源码部署预览

1. 从仓库复制 `.env.example` 为 `.env`，准备 `data/` 与 `backups/` 目录。
2. 在 `.env` 中设置浏览器实际访问的 `POCKET_TALLY_PUBLIC_ORIGIN=https://<域名>`，将 `POCKET_TALLY_BIND_ADDRESS` 设为 `127.0.0.1`，确认认证启用。将 `POCKET_TALLY_IMAGE_TAG` 改为仅供本机源码构建使用的标签，例如 `dev`，避免与 v0.1.0 正式镜像混淆。
3. 配置 HTTPS 反向代理，将同源请求转发到宿主机的前端端口；不要直接发布 FastAPI 端口。先确认 TLS、访问控制及防火墙，再执行源码构建。

```bash
cp .env.example .env
mkdir -p data backups
# 按上文编辑 .env，并完成 HTTPS 反向代理配置
docker compose up -d --build
```

首次启动且鉴权库为空时，在后端容器初始化唯一所有者：

```bash
docker compose run --rm backend pocket-tally-auth init --username owner
```

命令会交互提示设置密码。随后通过配置的 HTTPS 地址访问应用并登录。检查 `docker compose ps`、前端访问及 `/api/v1/health`；健康检查不能替代登录与备份验证。认证、会话与恢复命令见[认证与会话](authentication.md)。

## 备份与恢复

在录入真实数据及每次升级前，先创建账本备份，并用命令实际输出的文件名校验：

```bash
docker compose run --rm backup create
docker compose run --rm backup verify <上一步输出的备份文件名>
```

将校验后的副本保存到独立存储。账本备份**不包含**独立的登录凭据与会话库；需对鉴权数据制定单独的加密主机备份策略。恢复账本前先停止前后端，执行恢复并重新启动，再核对健康状态与关键账目：

```bash
docker compose stop frontend backend
docker compose run --rm backup restore <备份文件名> --confirm
docker compose up -d
```

恢复会替换当前账本，执行前应确认备份来源及影响范围。密码重置与会话撤销使用[认证与会话](authentication.md)中的受支持命令，不要手工修改数据库。

## v0.2.0 发布门槛

发布时才把本页的预览标识切换为正式版本，并核对实际镜像标签、Compose 默认值、升级与回退步骤、鉴权数据备份、健康检查及发行说明。未完成这些核对前，不将源码构建流程描述成已验证的正式镜像部署。
