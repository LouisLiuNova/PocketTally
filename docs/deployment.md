# Docker Compose 内网部署

PocketTally v0.1.0 提供 `frontend`、`backend` 两个业务容器和一个按需备份工具，支持
macOS ARM64 与 Linux x86_64。SQLite 数据和备份均保存在宿主机绑定目录中。v0.1.0
是首个已发布的 SQLite 数据库基线。

> [!WARNING]
> 当前版本没有登录鉴权，只允许部署在可信内网。不得在路由器上转发端口，不得给容器
> 分配公网入口，也不得直接部署到公网 VPS。默认端口 `54425` 只是高位端口，不是安全
> 措施；公网发布必须等待 `v0.2 公网单用户发布` 里程碑的鉴权任务完成。

## 前置条件

- Docker Engine 或 Docker Desktop，并支持 `docker compose`。
- macOS 使用 Apple Silicon；Linux 使用 x86_64。镜像同时支持
  `linux/arm64` 和 `linux/amd64`。
- 宿主防火墙只允许可信局域网访问 TCP `54425`。
- 首次正式保存数据前，先确定 `data` 和 `backups` 所在磁盘会被宿主机备份，并准备一块
  独立磁盘或另一台设备保存已校验的备份副本。

检查默认端口是否已被占用：

```bash
lsof -nP -iTCP:54425 -sTCP:LISTEN
```

没有输出表示当前没有监听进程。若系统没有 `lsof`，也可以直接启动 Compose；Docker
会在端口冲突时拒绝启动，随后在 `.env` 中更换 `POCKET_TALLY_HTTP_PORT`。

## 使用 v0.1.0 正式镜像首次启动

正式部署必须固定 `POCKET_TALLY_IMAGE_TAG=0.1.0`，不得依赖可变的 `latest`。
`.env.example` 已提供该固定值：

```bash
cp .env.example .env
mkdir -p data backups
docker compose pull frontend backend
docker compose up -d --no-build
```

Linux 用户建议把 `.env` 中的 UID/GID 改为当前用户，便于在宿主机管理文件：

```bash
id -u
id -g
```

macOS Docker Desktop 可以保留默认 UID/GID。Compose 的 `permissions` 一次性服务只负责
准备绑定目录权限；后端和备份工具随后以非 root 用户运行。

启动后查看状态并检查完整访问链路：

```bash
docker compose ps
curl --fail http://127.0.0.1:54425/api/v1/health
```

首次保存真实数据前，创建空账本基线备份并校验命令输出的实际文件名：

```bash
docker compose run --rm backup create
docker compose run --rm backup verify <上一步输出的备份文件名>
```

把校验通过的文件复制到独立存储后，才开始录入真实数据。

同一局域网的设备访问 `http://<宿主机局域网IP>:54425`。Compose 只发布前端端口；
FastAPI 的 `8000` 端口只在 Compose 网络内可见。若其他设备无法访问，应先检查宿主防火墙，
不要通过公网端口转发解决。

需要检查当前源码而不是部署发行版本时，可以使用 `docker compose up -d --build`。源码
构建不等于正式镜像部署，也不得用于绕过固定版本、备份或可信内网边界。

## 配置

根目录 `.env` 只供 Compose 使用且不会提交到 Git。主要配置如下：

| 配置 | 默认值 | 用途 |
| --- | --- | --- |
| `POCKET_TALLY_BIND_ADDRESS` | `0.0.0.0` | 前端在宿主机的监听地址。 |
| `POCKET_TALLY_HTTP_PORT` | `54425` | 前端在宿主机的端口。 |
| `POCKET_TALLY_DATA_DIR` | `./data` | SQLite 数据目录，可改为绝对路径。 |
| `POCKET_TALLY_BACKUP_DIR` | `./backups` | 一致快照目录，可改为绝对路径。 |
| `POCKET_TALLY_UID` / `POCKET_TALLY_GID` | `10001` | Linux 宿主机上的文件所有者；必须大于 0。 |
| `POCKET_TALLY_IMAGE_TAG` | `0.1.0` | 正式部署固定版本；不得改用可变的 `latest`。 |

数据库固定保存为数据目录中的 `pocket-tally.sqlite3`。不要手工编辑数据库，也不要让其他
程序写入该文件。

## 日志与日常操作

```bash
docker compose logs -f frontend backend
docker compose restart frontend backend
docker compose stop
docker compose up -d
```

容器日志使用 Docker `local` 驱动，每个服务最多保留 3 个约 10 MB 的轮转文件。业务日志
写到标准错误流，不在容器文件系统中保存日志文件。

## 备份、校验与恢复

服务运行期间可以使用 SQLite 在线备份 API 创建一致快照：

```bash
docker compose run --rm backup create
```

命令输出备份文件名，例如
`pocket-tally-20260909T120000.000000Z.sqlite3`。备份工具先写临时文件、执行
`PRAGMA integrity_check`，再原子改名。它不会自动删除旧备份，也不会自行定时运行；可以
从宿主机的定时任务调用上述命令。

随时校验指定备份：

```bash
docker compose run --rm backup verify pocket-tally-20260909T120000.000000Z.sqlite3
```

恢复会替换当前账本，必须先停止前后端：

```bash
docker compose stop frontend backend
docker compose run --rm backup restore pocket-tally-20260909T120000.000000Z.sqlite3 --confirm
docker compose up -d
curl --fail http://127.0.0.1:54425/api/v1/health
```

恢复前会在 `backups` 中自动创建 `pre-restore-*.sqlite3` 快照。源备份损坏、后端仍持有
账本进程锁、存在活动 journal/WAL 文件或未传入 `--confirm` 时，命令会失败并保留当前
数据库。

> [!IMPORTANT]
> 备份只有在另一块磁盘或另一台设备上存在副本时，才能抵御宿主磁盘故障。至少定期把
> `backups` 中已校验的文件同步到独立存储。

## 正式镜像地址、升级与回退

v0.1.0 标签流水线同时发布公开的 amd64/arm64 镜像。Compose 默认使用 GHCR；Docker
Hub 保存同版本副本。正式部署必须使用以下仓库的 `0.1.0` 标签：

GHCR 镜像：

- `ghcr.io/louisliunova/pockettally-frontend`
- `ghcr.io/louisliunova/pockettally-backend`

Docker Hub 副本：

- `iridium191/pocket-tally-frontend`
- `iridium191/pocket-tally-backend`

升级前先创建并校验备份，然后在 `.env` 中设置明确版本。v0.1.0 的配置为：

```dotenv
POCKET_TALLY_IMAGE_TAG=0.1.0
```

```bash
docker compose run --rm backup create
docker compose pull frontend backend
docker compose up -d --no-build
docker compose ps
curl --fail http://127.0.0.1:54425/api/v1/health
```

回退时把 `POCKET_TALLY_IMAGE_TAG` 改回上一个已验证版本，重新执行 `pull` 和 `up`，再做
健康检查。v0.1.0 是首个发布版本，没有更早的发行镜像可回退；若首次部署失败，应停止服务
并恢复开始录入前已校验的基线备份。

当前项目尚未建立版本化数据库迁移。后续 Schema 变更前必须建立迁移，或在对应发行说明
中明确兼容、升级前备份与恢复策略。未来版本若声明数据库不向后兼容，必须恢复匹配版本
的 SQLite 备份，不能只回退容器镜像。

## 镜像发布准备

版本发布前需要在 GitHub 仓库配置：

- Secret `DOCKERHUB_USERNAME`：有权写入 `iridium191` 镜像仓库的账号。
- Secret `DOCKERHUB_TOKEN`：该账号的 Docker Hub Access Token。
- GitHub Actions 对 Packages 的写权限；GHCR 使用内置 `GITHUB_TOKEN`。
- Docker Hub 的两个目标镜像仓库设置为公开。

GHCR 包要在首次推送后才会出现。首次标签任务可能在最后的匿名拉取验证阶段失败；此时
应立即把两个新建的 GHCR 包设为公开，再重新运行失败任务。匿名验证是公开发布的验收门禁，
不应跳过。

流水线只在 `vX.Y.Z` 标签上推送镜像，同时生成 `X.Y.Z`、`X.Y`、`X` 和 `latest`
标签、SBOM 与构建来源证明。PR 和 `main` 只执行双架构构建与冒烟测试，不发布镜像。
