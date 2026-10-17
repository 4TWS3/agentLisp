# US-03 交底：容器内可编译并运行一个 Agent（已达成）

> 判据：容器内可编译并运行一个 Agent
> 结果：**达成**。一条命令可复现。

---

## 1. 结论

`bash scripts/verify_container.sh` 退出码 0，编译与运行都通过。

---

## 2. 实测输出（本机 arm64）

```
arch:    aarch64
racket:  Welcome to Racket v8.7 [cs].
compile: OK (145 行)
run:     OK (harness=CHarness patterns=0 handlers=0)
```

---

## 3. 为什么不能直接用 release 镜像

| 问题 | 实测 |
|---|---|
| release 镜像平台 | 仅 linux/amd64 |
| 本机 | arm64 |
| `--platform linux/amd64` 模拟 | 基础命令 OK，`racket --version` → **Aborted** |
| Racket 官方 arm64 包 | **不存在**（安装包页面只有 x86_64-linux-bc） |

---

## 4. 解法

| 步骤 | 做法 |
|---|---|
| 基础镜像 | `python:3.12-slim-bookworm`（arm64 原生，不模拟） |
| Racket | Debian 源的 **8.7**（`apt install racket`） |
| apt 源 | 换 `mirrors.ustc.edu.cn`（`deb.debian.org` 在本机不通） |
| 验收 | 编译 `.al` → import 产物 → 实例化 Harness |

---

## 5. 边界（必须知道）

- 这是**验收脚本**，不是 release 镜像配方。release 镜像仍只有 amd64。
- 在 Racket 8.7 上验的是：编译 + 产物实例化。**RackUnit 全套未在 8.7 上跑**。
- 依赖 Debian 的 racket 8.7，与项目基线的 8.12 有版本差。

---

## 6. 未做

- 未改 release 镜像支持 arm64（要做需换 Racket 来源并跑全量回归）。
- 未在 Racket 8.7 上跑 RackUnit 全套。
