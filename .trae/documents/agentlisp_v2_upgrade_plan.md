# AgentLisp v2.0 架构升级实施计划

## Repository Research（现状调研）

**当前版本 v0.1 实际布局（已完成冒烟通过）：**

| 模块 | 当前路径 | 能力边界 |
|---|---|---|
| Scheme DSL | `scheme/agent-dsl/{main,reader}.rkt` | 纯宏 `define-agent/define-tool/define-workflow/atomic` + JSON 序列化，**无独立编译流水线、无 KV/Harness/Scope 静态断言、无 Python 代码发射器** |
| Python Runtime | `python/agentlisp_runtime/{models,engine,loader,cli}.py` | `AgentEngine` 以静态工作流为中心，**非 ReAct 循环、无 MCP 协议、无 Harness 管道抽象、无 BaseHarness 基类** |
| 基础设施 | `docker/docker-compose.yml` | 仅 app/dev/test/example 四个服务配置，**未部署 Redis/Temporal/Jaeger** |
| Python 依赖 | `python/pyproject.toml` | 仅有 pydantic/pyyaml/structlog/typer/rich，**缺失 anthropic/openai/mcp/fastapi/uvicorn/temporalio/redis/otel 全部核心栈** |
| 胶水层 | （无） | **无 FastAPI HTTP/SSE、无 Temporal Workflow/Activity、无 Docker/E2B 沙箱** |
| 产物结构 | （无） | **无 `examples/*.al` DSL 源码目录、无 `examples/dist/` 编译产物目录** |

**约束：**
- 已通过验证的 Python AST 解析、Loader 规范化、Engine 顺序执行链路必须在 v2.0 中**不回退**（作为 Harness 层的子能力保留或被封装）。
- 本次为**组件化骨架**落地，不等同于「全量业务功能实现」——代码生成器与三大静态断言、Temporal/FastAPI 先给出可扩展骨架与最小端到端示例；LLM/MCP/Redis/OTel 客户端封装留接口 + 可选依赖 group。

---

## Files and Modules（影响范围）

### A. 目录重构 / 新建

```text
agentLisp/
├── compiler/                                      ← 新增（取代旧 scheme/agent-dsl 逻辑）
│   ├── info.rkt
│   ├── main.rkt                                   ← CLI 入口：racket compiler/main.rkt xxx.al -o xxx.py
│   ├── parser.rkt                                 ← S-表达式 / .al 读取 & 语法糖展开
│   ├── checker.rkt                                ← 三大静态断言骨架：KV 对齐 / Harness 门控 / Scope
│   └── emitter.rkt                                ← Python 代码生成器（基于 jinja-like 模板字符串）
│
├── runtime/                                       ← 新增（原 python/agentlisp_runtime 部分迁移至此）
│   ├── __init__.py
│   ├── base_harness.py                            ← 核心：ReAct 循环 + Harness 管道（必写）
│   ├── memory_fs.py                               ← Markdown FS（L0/L1/L2 抽象，可接实际 FS / Redis）
│   ├── status_bar.py                              ← Context 尾部 Hook 接口
│   ├── llm_client.py                              ← LLM Provider 接口（OpenAI/Anthropic 双实现 + None 模式）
│   ├── mcp_client.py                              ← MCP Tool 调用抽象（可空实现）
│   └── checkpoint.py                              ← Checkpoint 抽象（Memory + Redis 两种实现）
│
├── host/                                          ← 新增
│   ├── __init__.py
│   ├── gateway.py                                 ← FastAPI 网关：HTTP/SSE 包装 Harness（最小健康 + /run 示例）
│   ├── workflow.py                                ← Temporal Activity/Workflow 骨架（未启用时走 DirectRunner）
│   └── sandbox.py                                 ← Docker / E2B 沙箱抽象（NullSandbox 默认实现）
│
├── examples/                                      ← 新增顶层
│   ├── repair_agent.al                            ← AgentLisp v2.0 DSL 最小示例（.al 后缀）
│   └── dist/                                      ← 编译产物（由 compiler/main.rkt 生成）
│       └── .gitkeep
│
├── infra/                                         ← 新增（根目录编排文件）
│   └── docker-compose.infra.yml                   ← Redis 7 / Temporal 1.24 auto-setup / Jaeger all-in-one
│
├── compiler-tests/ 或 compiler/tests/             ← RackUnit 三大断言 + emit 输出解析测试
│
└── scheme/ 与 python/                             ← 保持不变（v0.1 兼容层；README 注明迁移路径）
```

### B. 需变更的既有文件

| 文件 | 变更 |
|---|---|
| `python/pyproject.toml` | ①根移到 `pyproject.toml`（顶层 workspace 风格，sources = ["runtime", "host", "python"]）；②新增 `core`, `llm`, `mcp`, `web`, `durable`, `observability`, `sandbox` 可选分组 + `all`；③保留 ruff/mypy/pytest 配置并适配新路径 |
| `docker/Dockerfile{,.dev}` | 新增目录同步进镜像；增加可选 `INSTALL_OTEL=1`/`INSTALL_TEMPORAL=1` ARG（避免无意义膨胀） |
| `docker/docker-compose.yml` | 增加 `infra` profile 一键起 redis/temporal/jaeger（或 include `../infra/docker-compose.infra.yml`） |
| `.github/workflows/ci.yml` | 增加 compiler 测试（Racket）、runtime 测试（pytest）、host 冒烟（python -c "import host.gateway"） |
| `README.md` | 增加 v2.0 三层架构图、工作流 6 步命令、.al→.py 编译示例、SSE 调用示例 |
| `.gitignore` | 追加 `examples/dist/*.py`（除示例产物外忽略）、`*.al~` |

---

## Implementation Steps（依赖顺序）

> 共 9 步，无循环依赖。

1. **目录骨架 + 顶层 `pyproject.toml` 建立**
   - 新建 `compiler/ runtime/ host/ examples/ examples/dist/ infra/` 各目录及空 `__init__.py` / `.gitkeep`
   - 顶层 `pyproject.toml`（含 sources、可选依赖组）
   - 兼容：保留 `python/pyproject.toml` 但标注为 legacy，uv workspace 的形式链接过去（若困难则复制一份；顶层优先）

2. **Racket Compiler 四件套骨架**
   - `compiler/info.rkt` + `compiler/main.rkt`（CLI 参数 `-i/--input -o/--output --check-only --emit-python`）
   - `compiler/parser.rkt`：读取 `.al` S-表达式 → AST struct（agent/tool/harness/react-loop/workflow/hook）
   - `compiler/checker.rkt`：三大静态断言函数骨架 + 明确的 OK/NG 返回（默认宽松，空 agent 也能过；并留好断言注册表）
     - KV 对齐：tool.input_schema 字段与 AtomicAction params 命名匹配检查
     - Harness 门控：`(use-harness xxx)` 声明必须对应到 runtime 已注册 harness
     - Scope：workflow 内 step-id 不重复、next 引用存在
   - `compiler/emitter.rkt`：Python 模板字符串 emit，输出 `runtime.base_harness.BaseHarness` 的子类（保持输出可被 `ast.parse` 解析）

3. **`runtime/base_harness.py` 核心骨架（按建议先写）**
   - `BaseHarness`：__init__ 接收 (agent_cfg, llm_client, tool_registry, checkpoint_store, memory_fs, status_bar)
   - `run(inputs)` / `run_async(inputs)` 主入口
   - `_react_loop(max_turns=30)`：while 循环 → LLM call → tool dispatch → checkpoint → status_bar hook，无 LLM 时走 mock 路径确保可测
   - ReAct 结构体：`Thought / Action / Observation / Answer`，结构化到 `ExecutionTrace`

4. **配套 runtime 抽象（最小可运行实现）**
   - `memory_fs.py`：三层目录（L0 原子 / L1 概念 / L2 规则），MemoryFS + LocalFSBackend
   - `status_bar.py`：StatusBar Hook 协议（`on_step / on_done / on_error`）与 PrintingStatusBar 默认
   - `llm_client.py`：`LLMClient` protocol，`MockLLMClient(responses: list)` 用于测试
   - `mcp_client.py`：`ToolRegistry`，支持动态注册 + 调用（可选 MCP SDK 导入，未装时回退纯 Python）
   - `checkpoint.py`：`MemoryCheckpointStore` + `RedisCheckpointStore(可选，需要 redis lib)`

5. **Host 胶水层骨架**
   - `gateway.py`：FastAPI，路由 `/health`、`/v1/agents/{name}/run`(返回 run_id)、`/v1/runs/{run_id}`(SSE / JSON 双模式)；未启动时 import 不报错
   - `workflow.py`：`DirectRunner`（同步执行） + `TemporalRunner`（可选，未装 temporalio 时抛 NotImplementedError 可捕获）
   - `sandbox.py`：`NullSandbox` / `DockerSandbox`（后者可选依赖 docker lib）

6. **示例：`examples/repair_agent.al` + 编译产物验证**
   - 写最小 .al：声明 1 个 agent + 2 tools + 1 harness + 1 workflow
   - 执行 `racket compiler/main.rkt examples/repair_agent.al -o examples/dist/repair_agent.py`
   - 产物必须：① `ast.parse` OK；② 能被 `python -c "from runtime.base_harness import BaseHarness; import examples.dist.repair_agent as m; print(m.AGENT_NAME)"` 成功 import

7. **基础设施编排 `infra/docker-compose.infra.yml` + docker/ 扩展**
   - Redis 7-alpine、Temporal auto-setup 1.24（sqlite）、Jaeger all-in-one；端口与建议完全一致
   - `docker/docker-compose.yml` 顶层新增 `include: ../infra/docker-compose.infra.yml`（compose v2.20+ 支持，避免重复），并新增 `infra`/`all` profile

8. **CI 扩展 + 回归**
   - `.github/workflows/ci.yml` 新增 compiler 测试步骤 / runtime host 测试步骤
   - 本地执行两条独立验证命令：① Racket `raco test compiler/`；② Python `pytest runtime host python/tests`

9. **README v2.0 重写 + .gitignore 补充**
   - README：架构图、目录、6 步工作流、端口清单（6379/7233/8080/16686/4317 + gateway 默认 8000）、常见问题（未装 temporal 时如何降级 DirectRunner）
   - .gitignore：`examples/dist/*.py`、`__pycache__` 追加、*.al~

---

## Dependencies and Considerations

- **Racket 与 Python 双语言**：Compiler 产物必须 100% `ast.parse` 通过（第 6 步强制验证），避免手写模板字符串导致的语法错误。
- **可选依赖分组**：`fastapi/uvicorn/temporalio/redis/anthropic/openai/mcp/opentelemetry/docker` 全部走 optional-deps；默认 `uv sync` 只装 `core`，保证「无外部 API 也能完成最小冒烟」。
- **Docker Compose include**：使用 `include: ../infra/docker-compose.infra.yml` 语法，要求用户 Compose v2.20+（README 注明，不满足时手动 `docker compose -f infra/docker-compose.infra.yml up -d`）。
- **Temporal 资源消耗**：`auto-setup` 镜像较大（约 600MB+），默认 `infra` profile，非必启；runner 侧提供 DirectRunner 保证本地零依赖可跑。
- **向后兼容**：`scheme/` 与 `python/` 老目录不删除、不重写；CLI 与老示例继续工作，README 提供迁移对照表。
- **Windows x64**：保留 `release.yml` 中 PyInstaller 逻辑；新增目录被纳入 sources 时要同步 `pyinstaller --collect-all runtime --collect-all host`。

---

## Validation（验证清单，落地后逐条执行）

- [ ] 目录存在性：`compiler/ runtime/ host/ examples/ infra/` 齐全
- [ ] Racket：`cd compiler && raco pkg install --link . && raco test tests/`
- [ ] Compiler CLI：`racket compiler/main.rkt examples/repair_agent.al -o /tmp/out.py` 成功；`python -c "import ast; ast.parse(open('/tmp/out.py').read())"` 无异常
- [ ] Python 核心：`pytest runtime -v` BaseHarness mock 路径通过
- [ ] Host 导入：`python -c "import host.gateway; import host.workflow; import host.sandbox"` 无异常（缺可选依赖不崩溃）
- [ ] 基础设施：`docker compose -f infra/docker-compose.infra.yml up -d` → `curl http://localhost:8080` Temporal UI、`curl http://localhost:16686` Jaeger UI 返回 HTML
- [ ] CI 语法检查：`uv run ruff check runtime host`、`uv run mypy runtime`
- [ ] 原 v0.1 不回退：原冒烟命令 `cd python && python -c "…ALL CHECKS PASSED"` 依然打印相同结果

---

## Risks

1. **Racket emit 模板手写易出语法错** → 第 6 步强制 `ast.parse`；核心模板独立放入 `compiler/templates.py.txt`（若后续需要）+ 单元测试对比输出片段。
2. **顶层 pyproject workspace 与旧 python/pyproject 冲突** → fallback 方案：仅保留顶层一份，旧目录放 `python-legacy.txt` 说明；绝不维护两份重复依赖表。
3. **Temporal auto-setup 在某些 Docker Desktop 下启动慢/失败（端口 7233 不通）** → README 提供「DirectRunner 模式开关」环境变量 `AGENTLISP_RUNNER=direct`；CI 不启动 Temporal 真实端到端，仅 import-level smoke。
4. **Jaeger 镜像名建议原文拼写错误 `jaegertacing`** → 本计划按 `jaegertracing/all-in-one` 正确镜像实现。
5. **可选依赖未安装时 import 报 ImportError** → 在 `llm_client.py / mcp_client.py / checkpoint.py / gateway.py / workflow.py / sandbox.py` 中统一 `try_import` 模式，缺依赖时抛出带安装命令的异常类型（`FeatureNotInstalledError`）。
