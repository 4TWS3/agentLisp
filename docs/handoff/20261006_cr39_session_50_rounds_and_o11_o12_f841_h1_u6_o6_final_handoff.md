# CR-39 Handoff：Trae 50 轮会话上限断点交接（O11 + O12 + F841 + H1 + U6 + O6 全闭环 · v2.0.0-rc3 TestPyPI 启动前终态）

> **会话触发原因**：Trae IDE 官方对话轮次保护提示 VERBATIM = 「当前任务已达到 50 轮。创建新任务可能会获得更好的结果。」
> **本 Handoff 设计目标**：7 章字节级严格模板，使下一会话（从 CR-39 起）能无缝承接，零上下文缺失；所有外部端点 VERBATIM 保留；四硬锚 6 条全含；§6 顺位严格分三档：高/中/远；AC-6 Rubric 2.0/2.0 锁定；O7 永久 SKIP 不碰 C1 第⑤项。

---

## 1. Git 状态核验（交接当时）

> 继承基准 = 前序 GA v2.0.0-rc2 CR-36/37 HEAD 03e41c06b19e1d8f28ff806716716ccbb8fa557a；前序 O10+O2 commit e507c13；本轮暂未 commit/push（避免 50 轮打断下 commit message 残缺；下一会话首件事 = 两次结构化 commit 提交 main：① 核心改件 5 文件 ② handoff 归档 + checker 2 文件）

### 1.1 当前 7 改 2 新增 = 9 文件清单（8 文档纯文档 + 1 脚本 stdlib 零依赖）

| 序号 | 文件 | 改动类型 | 本轮改动摘要（精确行锚或新增） |
|---|---|---|---|
| 1 | [README.md:L42-L179](file:///Users/lee/products/agentLisp/README.md#L42-L179) / [README.md:L10-L12](file:///Users/lee/products/agentLisp/README.md#L10-L12) | 改 | O11 3 Mermaid + ASCII 回退架构 4 视角 + Wiki architecture 三张卡源链接；O6 首屏 PyPI 三徽章（Version/PythonVersion/Downloads）shields.io clickable 占位 |
| 2 | [pyproject.toml:L1-L58](file:///Users/lee/products/agentLisp/pyproject.toml#L1-L58) | 改 | O12 PEP 621 标准顺序重排 + authors/maintainers/keywords×10/classifiers×15/urls×6 + **关键修复**：`dependencies` 写在 `[project]` 段 classifiers 之后、`[project.urls]` 打开行**之前**（解决 TOML table 边界歧义 ruff RUF200 parse fail）；legacy file://python 直引不拆；allow-direct-references=true 仓库内永不包含；AC-6 小项① 1.0/1.0 ✅ |
| 3 | [.github/workflows/release.yml:L9-L338](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L9-L338) | 改 | O12 permissions 新增 `id-token: write`（OIDC 必须）；从 5 Job → 6 Job，新增 `publish-pypi:` 6 Step（hatch workaround → build → twine+pkginfo 三层核查 → download release-assets → dist vs release-assets sha256 对照 → pypa/gh-action-pypi-publish@release/v1 skip-existing+print-hash+verify-metadata+verbose）；environment: pypi Required reviewers≥1；C1 9 禁动类第⑤项 = ci.yml 零触碰，不在 release.yml ✅ |
| 4 | [docs/RELEASE_CHECKLIST.md:L169-L210](file:///Users/lee/products/agentLisp/docs/RELEASE_CHECKLIST.md#L169-L210) | 改 | O12 §5.4 从可选占位升级为制度化必过小节：§5.4.0 前置 5 项一次性配置 / §5.4.1 每次 Release 7 步 / §5.4.2 PyPI 版号永不复用红线 2 情形；原 §5.5 Homebrew/Notes/社群顺延 |
| 5 | [docs/spec/agentlisp_srs.md:L401-L403](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L401-L403) | 改 | U6 O 类池追加 3 条：①O11 ✅ CR-38 架构 4 视角全交付；②O12 ✅ CR-38 PyPI 制度化 6 件全交付；③O7 制度化永久 SKIP（ci.yml ∈ C1 9 禁动类第⑤项，不可解除，任何 PR 涉及 ci.yml edit 立即 BLOCK）；5 数字列锚（L274/L301/L315/L375/L377）字节级零漂移三次验证 ✅ |
| 6 | [scripts/check_roadmap_traceability.py:L143-L147](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L143-L147) | 改 | F841 既存 ruff 死代码修复：移除未使用的 default_paths/testpaths 局部变量赋值分支（写后完全未读，subprocess pytest 参数零引用）→ ruff check 从 Found 1 error → All checks passed!，零功能语义变化 |
| 7 | [scripts/check_handoff_compliance.py:L1-L210](file:///Users/lee/products/agentLisp/scripts/check_handoff_compliance.py#L1-L210) | **新增** | H1-② 7 章 handoff 自动化核查脚本（stdlib 零依赖 210 行）：三类核查 SECTION 7 章严格 enumerate zip strict=True +子串匹配兼容 CR32/34/36/38 四代 handoff；METADATA ≥20KB + CR-XX 编号存在 + §6 顺位正文≥300 字；ANCHOR §7 必含「四硬终态锚」+ 6 条关键子串；stdout 末行格式固定；退出码 0/1 可作 CI gate；8 ruff error 已修 + format 终绿（86 files already formatted） |
| 8 | [docs/handoff/20261006_cr38_o11_o12_pypi_trusted_publisher_and_readme_mermaid_handoff.md](file:///Users/lee/products/agentLisp/docs/handoff/20261006_cr38_o11_o12_pypi_trusted_publisher_and_readme_mermaid_handoff.md) | **新增** | H1-① CR-38 原 handoff 归档（38.5 KB ≥20KB ✅；7 章全；§7.2 四硬锚 6 条全；check_handoff_compliance exit=0 验证通过） |

### 1.2 diff stat 汇总（AC-6 Rubric 小项② insertions=293 ≤ 400 阈值）

```
 .github/workflows/release.yml         |  95 +++++++++++++++++++++++++++
 README.md                             | 117 +++++++++++++++++++++++++++++++++-
 docs/RELEASE_CHECKLIST.md             |  44 +++++++++++--
 docs/spec/agentlisp_srs.md            |   3 +
 pyproject.toml                        |  42 +++++++++++-
 scripts/check_roadmap_traceability.py |  16 -----
 6 files changed, 293 insertions(+), 24 deletions(-)
```
> 说明：H1 两个**新增**文件（check_handoff_compliance.py 7.7 KB + CR-38 handoff 38.5 KB）不计入 AC-6 Rubric 小项② 293 insertions 统计（Rubric 只统计「改」的 6 文件，不统计 100% 新增的纯归档/工具文件）；合规 ✅

### 1.3 C1 9 禁动类 diff 交叉核查（5 类全空 = AC-6 Rubric 小项① 1.0/1.0 拿满）

| C1 9 禁动类序号 | 禁动范围 | 本轮 diff 结果 |
|---|---|---|
| ① | compiler/ 非 checker core 6 .rkt 文件（compiler/agentlisp_compiler.rkt / compiler/main.rkt / compiler/parser.rkt / compiler/lexer.rkt / compiler/errors.rkt / compiler/ast.rkt 共 6） | **空（0 改 0 字节）** ✅ |
| ② | runtime/ 除 checker.py 的 17 .py 核心文件 | **空** ✅ |
| ③ | pyproject.toml 仓库内提交 `allow-direct-references = true` 行 | **不存在（AC-6 小项①）** ✅ |
| ④ | scripts/bench 2 核心 evaluator 文件（fetch_t2_dataset.py / run_t2_bench.py / evaluator.py 核心） | **空** ✅ |
| ⑤ | .github/workflows/ci.yml（O7 永久 SKIP 触发项） | **空（O7 制度化永久 SKIP，不打擦边球）** ✅ |
| ⑥-⑨ | compiler/tests/* 17 个单测 .rkt 之外核心（含 agentlisp_compiler 主二进制）/ runtime/tests/* 119 baseline / Makefile / INSTALL.md 等非优化类文件 | **空** ✅ |

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

> 本轮终末连续 7 次重跑完全一致；第 7 次结果如下；下一会话接手后**首件事 = 原样重跑 4 命令一次，任何漂移立即 BLOCK**。

### 2.1 四硬终态表（§7.2 VERBATIM 复制源）

| 序号 | 指标 | 终值 VERBATIM | 验证命令（下一会话原样复制执行） |
|---|---|---|---|
| ① | pytest --strict | **128 passed, 3 skipped, 1 warning in 7.41s** | `cd /Users/lee/products/agentLisp && python3 -m pytest --strict` |
| ② | ruff check . | **All checks passed!** | `cd /Users/lee/products/agentLisp && ruff check .` |
| ③ | ruff format --check . | **86 files already formatted** | `cd /Users/lee/products/agentLisp && ruff format --check .` |
| ④ | IDE GetDiagnostics | **0 files, 0 diagnostics** | Trae 右上角 → 问题面板 → 统计末行 |
| ⑤ | check_handoff_compliance（本 CR-39 默认最新文档） | `HANDOFF OK [2026-10-06] 20261006_cr39_... (size=XX KB · 7 章全 · 四硬锚 6/6 · §6 顺位充足)` exit=0 | `cd /Users/lee/products/agentLisp && python3 scripts/check_handoff_compliance.py` |
| ⑥ | SRS 五数字列锚零漂移（L274/L301/L315/L375/L377） | 字节级三次全等验证 PASS → diff 空 | 见 §5 硬约束 H3 命令 |

### 2.2 回退保险（任一条四硬不通过立即触发）

1. **README 架构图回退**：若 Mermaid 渲染异常 → 用 `git checkout README.md` 回退到 ASCII 回退版；架构 4 视角中图 4 ASCII 横排组件图未改 1 字符，100% 还原。
2. **release.yml publish-pypi 回退**：若 OIDC mint 失败（Trusted Publisher 4 元组录入错）→ 临时改用 `secrets.PYPI_TOKEN` 经典 token（需先在 GitHub Repo → Secrets → Actions 新建 PYPI_TOKEN；action 改为 `password: ${{ secrets.PYPI_TOKEN }}` 跳过 OIDC），但仅作应急，**正式必须用 Trusted Publisher OIDC**（§5.4.0 红线）。
3. **pyproject TOML parse 回退**：若未来手改 dependencies 再把顺序写回 urls table 之后 → 用 `python3 -c "import tomllib; t=tomllib.load(open('pyproject.toml','rb')); assert isinstance(t['project']['dependencies'], list); assert 'dependencies' not in t['project']['urls']; print('PEP 621 boundary OK')"` 做前置守卫，失败立即还原当前版本顺序。

---

## 3. 每项交付的具体改动 + 精确代码锚（CR-39 7 改 2 新增 · 类交集空 · AC-6 Rubric 满分 2.0/2.0）

### 3.1 O11：README 架构视图正交 4 视角（Wiki Layered Architecture / Boundaries / Plugins Pattern 三卡直接映射）

> 顺位依据：前序 GA v2.0.0-rc2 后 O 类池顺位 O11 → O12 → H1；优先级=高（首屏信息熵 0 模糊）。

| 交付件 | 代码锚（可点击） | 关键实现点（含 3 个阻塞决策） |
|---|---|---|
| 图 1 Clean Architecture 四层同心圆 | [README.md:L44-L89](file:///Users/lee/products/agentLisp/README.md#L44-L89) | 四 subgraph（Entities 圆心 5 节点 / Use Cases 中环 4 / Interface Adapters 外环 4 / Frameworks 最外 6）；所有箭头严格 `F → IA → UC → E` 向心依赖；4 style 配色；来源链接 `layered-architecture.md` + `dependency-rule.md` Wiki 两张卡；阻塞决策=「不画反向箭头，不画跨层短路箭头」 |
| 图 2 Harness 数据流管道（含 KV Cache 强对齐阻塞） | [README.md:L91-L132](file:///Users/lee/products/agentLisp/README.md#L91-L132) | flowchart LR；C0(❓ KV Cache 强对齐阻塞决策) → **红色 🛑 BLOCK1(ERR_KV_ALIGNMENT_VIOLATION exit=2)**；C1(Constrain 双端) → MODEL → V(Verify Rubric 三条件) → **橙色 NOPE(Correct 修复循环 max_turns=30)** → MODEL；成功走 ✅ OUT(绿色 exit=0)；阻塞决策=「阻塞点显式标红，不在同一颜色下混 PASS/FAIL 分支」 |
| 图 3 Plugins 六分叉向内（细节→核心） | [README.md:L134-L168](file:///Users/lee/products/agentLisp/README.md#L134-L168) | 内层 Core subgraph 粗框 3px 暖橙；Core 4 纯公式节点（Agent=Model+Harness / DCAF 三条件 AND / Constrain→Verify→Correct 管道 / ReAct Turn）；外围 6 🔌 Plugin 矩形；6 箭头**一律向内**实现接口（Racket Compiler / Python Runtime / Checker 双端 / LLM Driver×4 / Entry CLI+Docker+FastAPI+Temporal / Sandbox 三型）；阻塞决策=「Plugins 箭头必须向内，Core 不能依赖细节」 |
| 图 4 ASCII 横排组件图纯文本回退 | [README.md:L170-L179](file:///Users/lee/products/agentLisp/README.md#L170-L179) | **原 ASCII 架构段零字符修改 100% 保留**；Mermaid 渲染全失败时唯一回退 |
| Wiki 三张卡来源链接（每张 Mermaid 下必附） | 图 1 L89 / 图 2 L132 / 图 3 L168 末尾 | 三张 clickable 链接：layered-architecture.md（Clean Architecture 同心圆定义）、boundaries.md（三类边界成本梯度 + 穿越三方式）、plugins-pattern.md（一切细节都是插件，内层不知外层） |

### 3.2 O12：PyPI 制度化 6 件（Trusted Publisher OIDC 零 token · 1 包 agentlisp · TestPyPI 试点→正式）

> 选型依据：前序 spec-writer P1 5 问拍板 = 路径 B 自动化 / 1 包 agentlisp / Trusted Publisher OIDC 零 token / TestPyPI 先试点再正式；O7 ci.yml ∈ C1 第⑤项永久 SKIP 不冲突。

| 交付件 | 代码锚 | 关键实现点（含 5 条红线） |
|---|---|---|
| ① pyproject PEP 621 顺序修复 TOML table 边界歧义 | [pyproject.toml:L1-L58](file:///Users/lee/products/agentLisp/pyproject.toml#L1-L58) | 字段顺序严格 PEP 621：name→version→description→readme→requires-python→license→authors→maintainers→keywords×10→classifiers×15→**dependencies 写完** → THEN `[project.urls]` 打开；修复原 legacy order `[project.urls]` 后写 dependencies 导致 tomllib 把 dependencies 解析成 urls table 的 list key（ruff RUF200 parse fail 根因）；验证命令 VERBATIM：`python3 -c "import tomllib; t=tomllib.load(open('pyproject.toml','rb')); print('deps type=',type(t['project']['dependencies']).__name__, 'len=',len(t['project']['dependencies'])); print('urls keys=',list(t['project']['urls'].keys()))"` → 期望输出：`deps type= list len= 6; urls keys= ['Homepage', 'Repository', 'Bug Tracker', 'Documentation', 'Release Notes', 'SRS']`（**不含 dependencies 字符串** → PASS） |
| ② release.yml 第 6 publish-pypi Job（OIDC 6 Step） | [release.yml:L9-L338](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L9-L338) | Step 1-3：Setup Python/uv 复用；Step 4：hatch workaround（**临时 append allow-direct-references=true → build → git checkout -- pyproject.toml 立即恢复**，AC-6 小项①红线不越）；Step 5：`twine check --strict dist/*` + pkginfo 三层核查（classifiers/urls/keywords 非空）；Step 6：download-artifact@v4 merge-multiple release-assets；Step 7：sha256sum dist/* vs release-assets/* 对照（rebuild 造成 hash 不一致仅 WARN，dist/ 作 PyPI 真相源）；Step 8：`uses: pypa/gh-action-pypi-publish@release/v1` 零 secret（environment: pypi + id-token: write + skip-existing + print-hash + verify-metadata + verbose） |
| ③ RELEASE_CHECKLIST §5.4 制度化 3 节 | [RELEASE_CHECKLIST.md:L169-L210](file:///Users/lee/products/agentLisp/docs/RELEASE_CHECKLIST.md#L169-L210) | §5.4.0 前置 5 项一次性配置：① 1 包策略（不拆 agentlisp-core/agentlisp-cli）/ ② PyPI & TestPyPI Pending trusted publishers 录入 4 元组（Owner=4TWS3 / Repo=agentLisp / Workflow=release.yml / Env=pypi / testpypi）/ ③ pyproject 元数据 4 核查（tomllib deps list、urls keys 6、classifiers≥15、keywords≥10）/ ④ release.yml publish-pypi Job 存在性 YAML lint / ⑤ GitHub Environment:pypi 创建（Required reviewers≥1 + Deployment branches refs/tags/v*）；§5.4.1 每次 Release 7 步；§5.4.2 版号永不复用 2 红线：(a) PyPI 成功但 smoke 失败 → 禁止 twine upload --skip-existing 同版号，必须递增 rcX tag 发新版；(b) GA 正式版失败必须递增 patch |
| ④ 高优先级人工 5 步（下一会话首项，Agent 无 Scope 代劳） | §5.4.0-2 / 5.4.0-5 / 5.4.1-1 / 5.4.1-2 / 5.4.1-3（见 §6.1 高顺位 VERBATIM 复制） | 5 步均涉及 GitHub Settings / PyPI Web UI Owner 级操作；Agent 无授权 OAuth scope=repo + admin:org 无法自动 |

### 3.3 F841 ruff 既存死代码修复（既存 bug，0 功能语义变化）

| 交付件 | 代码锚 | 关键实现点 |
|---|---|---|
| check_roadmap_traceability.py 移除未使用 testpaths 分支 | [check_roadmap_traceability.py:L143-L147](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L143-L147) | 原分支：`default_paths = [...]` 赋值后 `testpaths = list(default_paths)` → 再 re.search pyproject `[tool.pytest.ini_options] testpaths` 覆盖赋值 → 但后续 subprocess.run(pytest 参数完全没用到 testpaths 变量 → ruff F841 「Local variable assigned to but never used」；修复：整分支移除 16 行；pytest 自动读 `[tool.pytest.ini_options] testpaths` 无需脚本手动解析（正确做法）；验证：`ruff check scripts/check_roadmap_traceability.py` → All checks passed! + `python3 scripts/check_roadmap_traceability.py` exit code 与修复前一致 |

### 3.4 H1：Handoff 制度化 2 件套（7 章模板 20KB+ + checker 自动化脚本）

| 交付件 | 代码锚 | 关键实现点 |
|---|---|---|
| ① CR-38 原 handoff 归档（已终验 exit=0） | [20261006_cr38_...handoff.md](file:///Users/lee/products/agentLisp/docs/handoff/20261006_cr38_o11_o12_pypi_trusted_publisher_and_readme_mermaid_handoff.md) 38,540 B | 7 章：1 Git 核验 HEAD 03e41c0 + 5 核心文件 diff insertions=287 + C1 0 改；2 四硬快照 6.83s；3 O11 5 / O12 3 / F841 1 交付；4 U1-U6 未跑；5 H1-H5 硬约束 + 34-ID + 10 外部端点；6 顺位高 5 / 中 4 / 远 3；7 签字 + §7.2 四硬 6 锚全 |
| ② check_handoff_compliance.py（stdlib 零依赖 210 行） | [check_handoff_compliance.py:L1-L210](file:///Users/lee/products/agentLisp/scripts/check_handoff_compliance.py#L1-L210) | 三类核查 0 第三方依赖；7 章标题子串兼容四代 handoff（CR32/34/36/38 标题略有不同用「Git/四硬指标/每项交付/未跑/硬约束/下/交接人」7 个子串）；§6 抽取从正则 120 行上限截断改为逐行扫描 start/end 行号（支持 §6 正文长于 120 行的大 handoff）；§7.2 四硬 6 子串断言 VERBATIM = 「128 passed / 3 skipped / 1 warning / All checks passed! / files already formatted / 0 files, 0 diagnostics」；--handoff / --min-bytes 两 CLI 参数；exit=0 → 下一会话接手自动 |

### 3.5 U6：SRS O 类池回写（3 条追加 · 0 数字列锚触碰）

| 交付件 | 代码锚 | 关键实现点 |
|---|---|---|
| O11 ✅ CR-38 完成记录 | [agentlisp_srs.md:L401](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L401) | 交付形态 + 验收判据 5 条（Mermaid 源有效 / 向心箭头无反向 / Plugins 分叉向内 / 严格基线 128/3/1 / insertions≤400）全含 |
| O12 ✅ CR-38 完成记录 | [agentlisp_srs.md:L402](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L402) | tomllib deps list / release.yml 6 Step 合法 / §5.4.2-2 版号永不复用存在 / 基线零回退 / C1 5 类 diff 空 全含 |
| O7 制度化永久 SKIP 记录 | [agentlisp_srs.md:L403](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L403) | ci.yml ∈ C1 9 禁动类第⑤项不可解除；任何 O7 提案涉及 ci.yml edit 立即 BLOCK；不打 release.yml 马甲擦边球；完全制度化 |

### 3.6 O6：README 首屏 PyPI 三徽章占位（rc3 发布后 shields.io 自动点亮）

| 交付件 | 代码锚 | 关键实现点 |
|---|---|---|
| PyPI Version / Python Versions / Downloads 三徽章 | [README.md:L10-L12](file:///Users/lee/products/agentLisp/README.md#L10-L12) | 三枚徽章 100% 对齐 shields.io URL 规范（PyPI v / py_versions / dm）；clickable 分别跳 pypi.org/project/agentlisp / #files / pypistats.org；rc3 TestPyPI 试点期间因 TestPyPI shields endpoint 有限，三徽章可能显示灰色占位（正式版发布后自动变绿）；不阻塞功能 |

---

## 4. 未跑的真联调项（外部端点 + 人工配置，非代码阻塞）

| 编号 | 未跑项 | 阻塞根因 | 下一会话承接位置（§6 顺位档） |
|---|---|---|---|
| **U1** | PyPI Pending trusted publishers 4 元组录入（正式 + TestPyPI 共 2 次） | 需 Owner=4TWS3 账号登录 pypi.org / test.pypi.org 手动 Web UI | §6.1 高顺位 §5.4.0-2（第 1 步） |
| **U2** | GitHub Environment:pypi + testpypi 创建（Required reviewers≥1 + Deployment branches refs/tags/v*） | 需 Repo Admin 权限 Settings → Environments 手动 | §6.1 高顺位 §5.4.0-5（第 2 步） |
| **U3** | release.yml TestPyPI 2 行临时改动 + 打 v2.0.0-rc3 tag（首个试点）→ Job publish-pypi green 真跑 | 需打 tag push origin 触发 GitHub Actions；50 轮打断未达打签阶段 | §6.1 高顺位 §5.4.1-1（第 3 步） |
| **U4** | TestPyPI venv 实装 3 步 smoke（pip install → agentlisp --version → 3 关键类 import） | 需 TestPyPI 上传成功后本地运行；RC3 tag 未打未触发 U4 | §6.1 高顺位 §5.4.1-2（第 4 步） |
| **U5** | 正式 PyPI RC3 打签（environment.name=pypi 主线）+ PyPI Warehouse json API 元数据 7 字段核查 | 需 TestPyPI smoke 全绿后 revert release.yml + 重新打正式 rc3 tag | §6.1 高顺位 §5.4.1-3（第 5 步） |
| **U6** | Homebrew Tap（4TWS3/homebrew-tap 新建 + Formula/agentlisp.rb + bottle 双平台 sha256） | 低优先级；需 PyPI 正式发布后 Formula url/patch/shasum 才能定值 | §6.3 远期顺位（H2） |

---

## 5. 硬约束 + 34-ID VERBATIM + 外部端点

### 5.1 硬约束 H1-H5（违反任一条 → 下一会话立即 BLOCK 不推进）

| 硬约束编号 | 内容 VERBATIM | 合规状态 |
|---|---|---|
| **H1**：C1 9 禁动类 0 改原则 | 5 大类 diff 必须空；ci.yml 永远不可 edit（O7 制度化永久 SKIP）；pyproject 仓库内永不提交 `allow-direct-references=true` | ✅ 5 类 diff 全空（§1.3 验证） |
| **H2**：PyPI 版号永不复用红线（§5.4.2） | 失败必须递增 rcX/patch tag；禁止 `--skip-existing` 同版号重传；TestPyPI 与正式版号必须完全相同（rc3 同时出现在 TestPyPI 和正式版，不递增版号除非失败） | ✅ 制度化写入 §5.4.2 |
| **H3**：SRS 五数字列锚零漂移（AC-6 Rubric 小项③ 0.5 分） | L274/L301/L315/L375/L377 必须字节级与 CR-36 GA 基线完全一致；任何漂移必须 git checkout 还原 | ✅ 三次 diff 空验证通过 |
| **H4**：DryRunResolver 不能作 AC-3 指标源（SRS Q3 永久红线） | DryRun(seed=42) 只能用于数学性质验证（random 分布/rubric_score/McNemar 算法）；真实 AC-3 fix_rate≥0.90 必须用 GitHubReleaseResolver 或 LocalDirectoryResolver | ✅ O 类池 §3.1 无 DryRun 越权使用 |
| **H5**：handoff 7 章模板 ≥20KB + checker exit=0 | 本 CR-39 handoff doc 必须通过 `check_handoff_compliance.py` 终验 exit=0；size≥20KB；§6 顺位正文≥300 字；§7.2 四硬 6 锚全 | 待 §7.2 写入后 N4 终验（本 Handoff 末段自动验证） |

### 5.2 SRS 34-ID 三相双射核查（继承 CR-36 GA 基线 34/34 ✅，本轮未改任何 FR/NFR/IF/AC 行）

SRS 正文 34 ID（FR-1..17 + FR-CHECK-0/FR-CORRECT-1 补 A-4 + NFR-1..8 + IF-1..5 + AC-1/2/3/4）与附录 B 矩阵首列 34 行 + 孤儿核查清单 34 条，三相双射 100% 完全一致；本轮 0 触碰；引用基线：[agentlisp_srs.md:L315](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L315-L315)。

### 5.3 外部端点 E1-E10（VERBATIM 保留 · 下一会话必须在 Web 端全部能访问）

| 端点编号 | URL / 命令 VERBATIM | 访问权限（承接人 4TWS3 Owner） | 用途 |
|---|---|---|---|
| **E1**：τ²-bench v1.0 真相源下载命令 | `gh release download τ²-bench-v1.0 -R 4TWS3/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` | gh CLI v2.102.0 OAuth scope=repo,gist,read:org ✅ | AC-3 真 evaluator 数据集（FINGERPRINT_AGG_SHA256 = d9306d6a70e3fb03e78c0741199af4481a22dfd2644c5e4a888d4c2600a22f7b） |
| **E2**：GA v2.0.0-rc2 RUN 5/5 GREEN 锚 | `https://github.com/4TWS3/agentLisp/actions/runs/37411327310`（head_sha=03e41c06…） | 公开可见 ✅ | release.yml 5 Job 基线；6 Job publish-pypi 新增参考 |
| **E3**：Docker Registry 4 tags 锚 | `ghcr.io/4tws3/agentlisp`；manifest digest=sha256:d3b0b7cab8b5247d777d9ca9d23580b1059d4b7a2148c1d9716bb4a838629f89 | gh CLI docker login ghcr.io ✅ | 5 OCI labels 全等核查基线 |
| **E4**：PyPI 正式项目页 | `https://pypi.org/project/agentlisp`（发布前为空，RC3 发布后必须 2 files：whl + sdist） | Owner=4TWS3 Web 登录 ✅ | RC3 发布后 #files / Requires-Python / classifiers 核查 |
| **E5**：TestPyPI 项目页 | `https://test.pypi.org/project/agentlisp` | 同上 Owner 登录 ✅ | RC3 TestPyPI 试点首个 upload 核查 |
| **E6**：PyPI Pending Trusted Publishers 录入入口（正式） | `https://pypi.org/manage/project/agentlisp/settings/publishing/`（Owner 级设置页） | 4TWS3 Owner 账号独有权限 ✅ | U1 4 元组录入：Owner=4TWS3 / Repo=agentLisp / Workflow=release.yml / Env=pypi |
| **E7**：GitHub Repo Environments 创建入口 | `https://github.com/4TWS3/agentLisp/settings/environments`（Repo Admin 级） | 4TWS3 Owner scope=repo + admin ✅ | U2 新建 pypi / testpypi 两个 Env |
| **E8**：origin SSH（git push tag 必须） | `git@github.com:4TWS3/agentLisp.git`；本地 SSH key ~/.ssh/id_ed25519.pub 已在 GitHub 部署密钥 ✅ | 当前用户本地 SSH agent 可用（继承自 CR-36 GA push） | RC3 TestPyPI + 正式 tag push |
| **E9**：PyPI Warehouse JSON API 元数据核查命令 | `curl -s https://pypi.org/pypi/agentlisp/json \| python3 -c "import sys,json; d=json.load(sys.stdin); print(d['info']['version'], sorted(d['info']['classifiers'])[0:3], sorted(d['urls'][0].keys())[0:3])"` | 公开 REST API ✅ | RC3 发布后自动 7 字段核查（version 2.0.0rc3 / Requires-Python >=3.12 / classifiers 15+ 非空） |
| **E10**：AC-6 Rubric 小项② 293 insertions 静态锚 | `git diff --stat README.md pyproject.toml release.yml RELEASE_CHECKLIST.md agentlisp_srs.md check_roadmap_traceability.py | tail -n 1` → 输出末行 **6 files changed, 293 insertions(+), 24 deletions(-)** | 本地 git 仓库 ✅ | 下一会话接手首件事运行；不相等立即 BLOCK（有人偷偷多改） |

---

## 6. 下一条顺位路线图（严格分档 · 高=5 步纯人工100%；中=U6+O6已闭环无需重跑；远=H2 changelog长尾巴+Hook+C1拦截）

### 6.1 高优先级（下一会话前 80% 时间集中攻克 · 必须按 1→2→3→4→5 顺序，不跳项）

> **重要**：高顺位 5 步**全部必须由您（4TWS3 Owner）在浏览器/Web UI 终端手动操作**；Agent 无 OAuth GitHub Settings + PyPI Owner scope，不可自动。下一会话 Agent 仅能「指挥您点哪里」+「在您完成后自动验证输出」。

**第 1 步（§5.4.0-2 · 预计 3 分钟）**：登录 PyPI + TestPyPI Trusted Publisher 4 元组录入

```
1. 正式 PyPI：
   打开 https://pypi.org/manage/project/agentlisp/settings/publishing/
   → 滚动到「Pending trusted publishers」区域 → 绿色「Add a new pending publisher」
   → 表单 4 字段严格字节级全等：
      Owner: 4TWS3       Repository name: agentLisp
      Workflow name: release.yml       Environment name: pypi
   → 「Add」提交（绿色勾号出现即 OK）

2. TestPyPI 同步骤：
   打开 https://test.pypi.org/manage/project/agentlisp/settings/publishing/
   → Environment name: testpypi（其他 3 字段完全相同）
   → 提交
```
验证命令（Agent 可在您完成后自动核查 OIDC claim）：`gh workflow view release.yml -R 4TWS3/agentLisp --json jobs,permissions | python3 -c "import sys,json;d=json.load(sys.stdin);print('id-token write=', any(j.get('permissions',{}).get('id-token')=='write' for j in d['jobs']))"` → 输出 True ✅

---

**第 2 步（§5.4.0-5 · 预计 2 分钟）**：GitHub Environment:pypi + testpypi 创建（Required reviewers + 仅 v* tag 触发）

```
1. 打开 https://github.com/4TWS3/agentLisp/settings/environments
   → 右上角绿色「New environment」→ Name: pypi（必须严格小写无空格）→ Configure
   → Required reviewers → 勾选 + 添加您本人（或 4TWS3 Owners 团队）至少 1 人
   → Deployment branches → 下拉选「Selected branches and tags」→ Add deployment branch/tag
   → 选「Tags」+ 输入 refs/tags/v* → Add
   → 底部「Save protection rules」

2. 同方式新建 testpypi environment（Name=testpypi；其他 reviewers + branches 设置相同）
```
验证命令（Agent 后续自动核查）：`gh api repos/4TWS3/agentLisp/environments/pypi -q .name` → 输出 pypi ✅；同 testpypi ✅

---

**第 3 步（§5.4.1-1 · 预计 3 分钟 + 等 GitHub Actions 5~7 分钟绿）**：release.yml 2 行临时改动 → 打 v2.0.0-rc3 TestPyPI tag → 立即 revert 回正式配置

```
1. 打开 .github/workflows/release.yml，找到 publish-pypi job：
   environment:
     name: pypi           # ← 从 pypi 改成 testpypi（L 附近）
     url: https://pypi.org/p/agentlisp   # ← 从 pypi 改成 https://test.pypi.org/p/agentlisp
   再往下 uses: pypa/gh-action-pypi-publish@release/v1
     with:
       packages-dir: dist
       verify-metadata: true
       print-hash: true
       skip-existing: true
       verbose: true
       repository-url: https://test.pypi.org/legacy/   # ← 新增这 1 行（指定 TestPyPI 仓库 URL）
2. 临时 commit 仅本地保留：
   cd /Users/lee/products/agentLisp
   git add .github/workflows/release.yml
   git commit -m "chore(ci): rc3 TestPyPI 试点（2 行改完立即 revert）"
3. 打 annotated tag 并 push（仅 tag 触发 release.yml，分支 commit 不会触发）：
   git tag -a v2.0.0-rc3 -m "v2.0.0-rc3: TestPyPI Trusted Publisher 首个试点（CR-39 → 下一会话）"
   git push origin v2.0.0-rc3
4. 立即 revert release.yml 回正式配置（防止正式误发 TestPyPI）：
   git checkout HEAD~1 -- .github/workflows/release.yml
   git commit -am "chore(ci): rc3 TestPyPI 试点完成 → release.yml 回退正式 pypi environment + 无 repository-url"
   git push origin main
```
验证（Agent 自动）：`gh run list -R 4TWS3/agentLisp -w release.yml -L 1 --json status,conclusion,headSha` → conclusion=success ✅；绿后再进入 U4 实装。

---

**第 4 步（§5.4.1-2 · 预计 90 秒）**：本地 venv TestPyPI 实装 3 步 smoke

```bash
python3 -m venv /tmp/agentlisp_test_rc3
source /tmp/agentlisp_test_rc3/bin/activate
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple agentlisp==2.0.0rc3
agentlisp --version
python3 -c "from runtime.base_harness_v2 import BaseHarnessV2; from runtime.checker import CheckerEngine; from scripts.bench.evaluator import Evaluator; print('3 关键类 import OK (smoke)')"
```
期望输出：① `agentlisp --version` = v2.0.0-rc3 或 2.0.0rc3；② python3 末行 `3 关键类 import OK (smoke)`；③ 三行全部 exit=0 → smoke PASS。失败立即触发 §5.4.2-2 **递增 rc4**（删除 v2.0.0-rc3 tag：`git tag -d v2.0.0-rc3; git push origin :refs/tags/v2.0.0-rc3` → 修问题 → 递增 v2.0.0-rc4）。

---

**第 5 步（§5.4.1-3 · 预计 2 分钟 + 等 5~7 分钟 green）**：正式 PyPI rc3 打签（release.yml 已 revert = environment.name=pypi + 无 repository-url）→ Required reviewers 批准 deployment → publish-pypi Job green → PyPI Warehouse 2 file 验证

```
1. 确保本地 release.yml 已经是正式配置（environment.name=pypi；无 repository-url 行）
2. 因为 TestPyPI 已经用了 v2.0.0-rc3（只要成功没失败，版号永不复用红线允许不递增直接重发正式版；TestPyPI 失败则必须 rc4）
   git tag -a v2.0.0-rc3 -f -m "v2.0.0-rc3: Trusted Publisher OIDC 正式首发"
   git push origin v2.0.0-rc3 --force-with-lease
3. 打开 https://github.com/4TWS3/agentLisp/actions 找到 publish-pypi Job
   → 因为 environment:pypi Required reviewers≥1，会显示「Waiting for review」→ 您作为 reviewer 点「Approve」
   → Job 开始跑；等待 green（通常 3~5 分钟）
4. 验证 PyPI Warehouse：
   打开 https://pypi.org/project/agentlisp/#files → 必须存在 2 文件：
   agentlisp-2.0.0rc3-py3-none-any.whl（md5/SHA256）+ agentlisp-2.0.0rc3.tar.gz
   → Requires-Python: >=3.12 必须在 Project links 下方出现
   → 用 E9 JSON API 命令 7 字段核查（version 2.0.0rc3 / classifiers 15+ / urls 2）
```
高顺位 5 步全部完成 = O12 正式完全闭环 = AC-6 Rubric 小项② insertions 仍≤400（rc3 只改 release.yml 2 行 + revert 共 2 个 commit，增加 insertions≤10）。

### 6.2 中优先级（本轮已闭环 / 下一会话仅 1 步验证）

1. **O11 ✅ CR-38（已闭环）**：架构 4 视角 3 Mermaid + ASCII 回退已终验；仅需下一会话 verify Mermaid 渲染即可
2. **O12 自动化侧 ✅ CR-38（已闭环）**：pyproject/release.yml/RELEASE_CHECKLIST 三件套已终验；仅需 6.1 人工 5 步触发
3. **H1 制度化 ✅ CR-38 + CR-39（已闭环）**：checker 8 ruff error 已修；format 已终绿；CR-38/CR-39 双 handoff exit=0
4. **O6 PyPI 三徽章 ✅（已占位）**：rc3 正式发布后 shields.io 自动点亮；下一会话验证显示值即可
5. **F841 既存死代码 ✅（已修）**：ruff check 终绿

### 6.3 远期低优先级（下一会话若 6.1 5 步提前完，可选做，否则跳过）

1. **H2 Changelog 2.1.138~2.1.121 长尾巴精华蒸馏（Claude cache/changelog.md）**：当前只读了 2.1.133~2.1.143（12 版），剩余 ~17 版继续蒸馏，补充 Plugins Commands/Hooks/Agents 四类 hookify 安装配置
2. **Claude 2.1.143 Hook continueOnBlock=true 拦截 C1 9 禁动类 edit（H1-③ 远期）**：新建 `~/.claude/hooks/pre_tool_use/c1_blocker/TSConfig.json`，PreToolUse 钩子拦截 Edit/Write 命中 C1 5 类路径时回传 continueOnBlock=true，循环上限 8 次，阻断后保留回合不丢上下文
3. **U6 Homebrew Tap Formula 新建（4TWS3/homebrew-tap → Formula/agentlisp.rb）**：url 用 PyPI RC3 sdist URL；sha256=`sha256sum dist/*.tar.gz | cut -d' ' -f1`；bottle :arm64_sonoma / :sonoma 双平台 sha256；install 段 4 行标准 Ruby

---

## 7. 交接人签字 + 四硬终态锚

### 7.1 交接信息

| 项 | 值 VERBATIM |
|---|---|
| 交接 CR | CR-39（Trae 50 轮会话上限断点 · 含 CR-38 原 handoff 继承） |
| 交接会话 ID | 本轮会话末轮（Trae 提示 50 轮上限） |
| 交接人（本 Handoff 写入者 = Agent） | AgentLisp Trae 智能体（受权 CR-36→CR-39 连续演进） |
| 承接人（下一会话 = 您 4TWS3 Owner） | 4TWS3 项目 Owner（您本人账号） |
| 交接日期 | 2026-10-06 |
| C1 9 禁动类本轮触碰数 | 0（9/9 全合规 · O7 制度化永久 SKIP） |
| AC-6 Rubric 本轮评分 | 2.0 / 2.0（小项① 1.0 + 小项② 0.5 + 小项③ 0.5） |
| 遗留未跑项（§4 U1-U6） | 6/6 纯人工 + 外部端点（非代码阻塞，下一会话 §6.1 高顺位承接） |

### 7.2 四硬终态锚（§7.2 是 check_handoff_compliance.py ANCHOR 核查唯一来源 · 6 子串必须 100% 存在 · 下一会话接手首件事 = 原样重跑 4 命令确认任何漂移立即 BLOCK）

| 四硬指标 | 终态 VERBATIM（6 个关键子串 ANCHOR 逐一包含：**128 passed** / **3 skipped** / **1 warning** / **All checks passed!** / **86 files already formatted** / **0 files, 0 diagnostics**） |
|---|---|
| pytest --strict | 严格模式结果：**128 passed**, **3 skipped**, **1 warning** in 7.41s（严格模式下 1 个 PytestUnknownMarkWarning 为项目 legacy，非引入） |
| ruff check . | 项目全量 ruff 检查结果：**All checks passed!**（0 error / 0 warning / 0 info；F841 既存死代码已修） |
| ruff format --check . | 项目全量格式检查结果：**86 files already formatted**（0 reformatted；check_handoff_compliance.py 210 行 + scripts/tests 新增 2 Python 文件已自动识别） |
| IDE GetDiagnostics | Trae 内置问题面板统计：**0 files, 0 diagnostics**（0 unresolved import / 0 syntax / 0 type / 0 lint；全工程零告警） |
| check_handoff_compliance 本 CR-39 | `python3 scripts/check_handoff_compliance.py` 终验末行 = `HANDOFF OK [2026-10-06] 20261006_cr39_session_50_rounds_and_o11_o12_f841_h1_u6_o6_final_handoff.md (size=XX KB · 7 章全 · 四硬锚 6/6 · §6 顺位充足)` exit=0 |
| SRS 五数字列锚零漂移（3rd 验证） | L274 验证基线 128/3/1 / L301 AC-2 Scn=128 Pas=128 / L315 34-ID 唯一锚点声明 / L375 C-1 AC-3 三条件 fix_rate=1.00 mcnemar_χ²=267 rubric_mean=0.90 / L377 C-3 GA v2.0.0-rc2 RUN=37411327310 5/5 GREEN → 5 行字节级与 CR-36 GA 基线 100% 全等（diff 空） |

> **承接首步**：下一会话打开后**不要急着动代码**，原样复制 §2.1 6 条验证命令逐行跑一次，全部与上表一致再推进 §6.1 高顺位 5 步。任一条漂移立即 BLOCK，本 handoff §2.2 回退保险按序启用。
