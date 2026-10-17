# US-03 交底：独立开发容器（阻塞：arch 不匹配）

> 判据：容器内可编译并运行一个 Agent

---

## 1. 结论

**阻塞。** Docker 可用，镜像也有，但**本地跑不了**。

---

## 2. 实测证据

| 项 | 值 |
|---|---|
| Docker 守护进程 | 已启动（server **28.0.1**） |
| 发布镜像 | `ghcr.io/4tws3/agentlisp:v2.3.1`（**仅 linux/amd64**） |
| 本机 | **arm64**（Apple Silicon） |
| 直接 pull | `no matching manifest for linux/arm64/v8` |
| 用 `--platform linux/amd64` pull | 成功 |
| 容器基础命令 | OK（`uname -m`=x86_64；`ls /app` 正常） |
| **`racket --version`（模拟运行）** | **Aborted** |

结论：Racket VM 在 x86_64 模拟下起不来。这是模拟层的问题，不是镜像的问题。

---

## 3. 镜像本身没问题

CI 的 `Docker Build` job **绿**（run `39037799389`），构建期自检通过。也就是说：
- 镜像能构建；
- 构建期在 amd64 上跑过编译自证。

---

## 4. 未做

- **arm64 镜像**：Dockerfile 里 Racket 装的是 `x86_64-linux-bookworm` 安装包；
  Racket 8.12 的 aarch64 安装包 URL 探测 404（未找到）。
- dev 容器（`docker/Dockerfile.dev`）同样只有 x86_64。

---

## 5. 能怎么解

| 方案 | 代价 |
|---|---|
| 在 amd64 主机/CI 上跑验收 | 需要那台机器 |
| 改 Dockerfile 用 arm64 的 Racket（发行版源里装） | 要改镜像配方 + CI 矩阵 |
