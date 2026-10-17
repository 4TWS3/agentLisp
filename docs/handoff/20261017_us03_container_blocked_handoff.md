# US-03 交底：独立开发容器（阻塞：Racket 无 aarch64 安装包）

> 判据：容器内可编译并运行一个 Agent
> 结果：**阻塞**。但修掉了一个真 bug（dev 镜像的下载地址是死的）。

---

## 1. 结论

容器跑不了，不是配置问题，是 **Racket 8.12 没有 Linux aarch64 安装包**。
同时发现并修掉了 dev 镜像的一个死地址。

---

## 2. 已修的真 bug

`docker/Dockerfile.dev` 原来写：
```
racket-minimal-8.12-x86_64-linux-${DEBIAN_VERSION}.sh   # DEBIAN_VERSION=bookworm
```
实测该 URL **404**（S3: NoSuchKey）。也就是说 **dev 镜像原本就构建不出来**。

| 项 | 修前 | 修后 |
|---|---|---|
| 安装包名 | `...-x86_64-linux-bookworm.sh`（404） | `...-x86_64-linux-bc.sh`（301→200） |

与 `docker/Dockerfile` 保持一致。

---

## 3. 阻塞证据（实测）

| 项 | 值 |
|---|---|
| Docker 守护进程 | 已启动（server 28.0.1） |
| 发布镜像 | `ghcr.io/4tws3/agentlisp:v2.3.1`，**仅 linux/amd64** |
| 本机 | **arm64**（Apple Silicon） |
| 直接 pull | `no matching manifest for linux/arm64/v8` |
| `--platform linux/amd64` pull + 基础命令 | OK |
| **`racket --version`（模拟 amd64）** | **Aborted** |
| Racket 8.12 Linux 安装包页面 | **只有 `x86_64-linux-bc`**，无 aarch64 |

---

## 4. 为什么不能本地绕过

| 方案 | 为什么不行 |
|---|---|
| 用官方 arm64 安装包 | Racket 8.12 **没有** Linux aarch64 安装包 |
| 模拟 amd64 | Racket VM 在模拟下 Aborted |
| 从源码编译 Racket | 30-60 分钟，且未验证 |

---

## 5. 能怎么解

| 方案 | 代价 |
|---|---|
| 换 arm64 的 Racket 来源（Debian `apt install racket`，8.7） | 要验证我们的编译器在 8.7 上能跑 |
| 在 amd64 机器/CI 上跑验收 | 需要那台机器 |
| 只发 amd64 镜像 | 现状，arm64 用户用不了 |

---

## 6. 未做

- 未验证 `apt install racket`（Debian 8.7）能否编译本项目。
- 未构建 arm64 镜像。
- 未在 amd64 机器上跑容器验收。
