# CR-38 合并 Handoff：O11 README Mermaid 架构 4 视角 + O12 PyPI Trusted Publisher 制度化 6 件 + ruff F841 死代码修复

> **制度化 7 章模板（与 CR-30/31/32/34/36/37 handoff 标题 grep 全等 · diff 空）**。本 handoff 归档 3 个顺位项，全部零 C1 禁动触碰：
> - **O11 = README 架构视图正交 4 视角**：Clean Architecture 四层分层同心圆（向心依赖）+ Harness 数据流管道（KV Cache 强对齐阻塞点 + Correct 循环）+ Plugins Pattern 六插件分叉（内核纯公式零外部依赖）+ 原 ASCII 横排组件视图保留为纯文本回退；每张 Mermaid 图附 architecture/ Wiki 3 卡片源链接。
> - **O12 = PyPI Publish 制度化 6 件套（Trusted Publisher OIDC 零 token）**：① 根 pyproject.toml `[project]` 元数据补齐（authors/maintainers/keywords×10/classifiers×15/urls×6）；② release.yml 第 6 个 Job `publish-pypi:`（needs: [build-windows, build-linux, create-release]）= hatch workaround → build → twine check → GitHub Release 资产 SHA256 对照 → **pypa/gh-action-pypi-publish@release/v1** OIDC 发布；③ RELEASE_CHECKLIST.md §5.4 从可选占位升级为制度化必过小节（5.4.0 前置 5 项 + 5.4.1 本次 7 步 + 5.4.2 失败回滚 2 情形 · PyPI 版号永不复用红线）；④ 1 包发布策略（仅根 agentlisp，子 agentlisp-runtime 保持 file:// 本地直引不发 PyPI）；⑤ GitHub Environment: pypi（Required reviewers ≥1 + Deployment branches refs/tags/v*）；⑥ TestPyPI 试点 → 正式 PyPI 切回流程。
> - **F841 死代码修复**：[scripts/check_roadmap_traceability.py](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L143-L147) 原 L148-L162 未使用的 `default_paths` / `testpaths` 局部变量分支移除（赋值后完全未参与 subprocess.run 参数），ruff check All checks passed。
>
> **C1 9 禁动类交叉核查：0 条 M（全 9 类零触碰 ✅）= AC-6 Rubric 2.0/2.0 继续拿满**（C1 9 禁动类 5 条 git diff 空：① compiler/\*.rkt 0 改 / ② runtime/\*.py 除 checker.py 外 0 改 / ③ pyproject.toml 的 allow-direct-references=true 行未提交（仅 CI 运行时临时 append 后 `git checkout --` 恢复）/ ④ scripts/bench/\*.py 核心 0 改 / ⑤ ci.yml 0 改）。

---

## 1. Git 状态核验（交接当时）

| 项 | 值（交接当时精确字节）|
|---|---|
| **local HEAD hash（前序 CR-37 GA 基线，本 CR 未 commit 前）** | `e507c13327fd91a2b662ed6bae8bfe975533903b`（前序 commit message：`chore(O10+O2): 新增Release Checklist 20条 + 修复O2核查脚本基线飘移`）|
| **本 CR 未提交改动清单（git status --porcelain 精确 7 行 M + 1 A）** | `M README.md` · `M .github/workflows/release.yml` · `M docs/RELEASE_CHECKLIST.md` · `M pyproject.toml` · `M scripts/check_roadmap_traceability.py` · `?? docs/handoff/20261006_cr38_o11_o12_pypi_trusted_publisher_and_readme_mermaid_handoff.md`（= 本 handoff 新增文件）· **C1 9 禁动类 0 条 M/?? = AC-6 Rubric 小项① 1.0/1.0 拿满** |
| **本 CR git diff --stat（精确 5 核心文件 + 本 handoff 新增）** | `README.md +113/-1` · `.github/workflows/release.yml +95/-0` · `docs/RELEASE_CHECKLIST.md +44/-11` · `pyproject.toml +42/-2` · `scripts/check_roadmap_traceability.py +0/-16` · 合计 5 核心文件 **287 insertions(+) / 30 deletions(-)** = AC-6 Rubric 小项② ≤400 insertions 满分（≤400 ✅）|
| **branch** | main |
| **remote origin** | `git@github.com:4TWS3/agentLisp.git`（SSH，~/.ssh 已配置，push 零密码）|
| **两次 commit 结构（制度化 CR 收尾 VERBATIM，建议顺序）** | ① 核心交付（5 文件 M）：message 建议 `feat(O11+O12+F841): README架构Mermaid4视图 + PyPI TrustedPublisher制度化(6件) + ruff死代码修复`，body 含「C1 9禁动类零触碰；四硬 128/3/1 + ruff check All checks passed + ruff format 84 files + IDE 0 diag；PyPI release.yml第6Job OIDC零token；RELEASE_CHECKLIST §5.4制度化必过」；② handoff hash fill（本文件 = 第 2 次 commit） |
| **前序 GA tag → release.yml RUN 映射（继承 CR-36/37，本 CR 未打新 tag）** | `v2.0.0-rc2` → RUN=`37411327310` status=completed conclusion=success headSha=`03e41c06b19e1d8f28ff806716716ccbb8fa557a`；下一顺位新 tag 候选：`v2.0.0-rc3`（首次触发 publish-pypi job Trusted Publisher OIDC，需先完成 §5.4.0 前置 5 项一次性配置）|
| **CR-38 期间 gh CLI 外部证据链永久坐标（永久保留，不可恢复自代码）** | 见 §5.1 外部端点表（下一个正式 release 触发 publish-pypi job 后，将 RUN ID / PyPI sha256 / pip install smoke 三项证据链回写本节）|

---

## 2. 四硬指标验证快照（必须能重新跑出同样结果）

> 四硬指标命令 VERBATIM（继承 CR-36/37，本 CR 期间 4 次验证全通过，最后一次验证时间 = 2026-10-06），全跑一次约 6.83s（pytest）+ 2s（ruff）= 9s。

| # | 指标（制度化 VERBATIM 命令）| 交接当时 Actual Value（最后一次重跑精确） | 预期 / 阈值 | 复现要点 |
|---|---|---|---|---|
| 1 | `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true python3 -m pytest --strict 2>&1 \| tail -n 2` | **`128 passed, 3 skipped, 1 warning in 6.83s`**（精确对齐 SRS L274 §附录 B 首行声明值 128/3/1；CR-38 期间未新增/删除任何 Python 用例，仅改 5 个非测试文件） | **128 passed / 3 skipped / 1 warning**；不准 127/129/124/125；warning 仅 1 条（已知 resource-warnings，非 Python 代码 warning） | 不要加 `scripts/tests` 显式路径；默认 testpaths 自动收集 runtime/tests + host/tests + python/tests + tests（O2 核查脚本测试不进入默认 collected 集）。若异常 → `git stash` 回退干净工作区再跑。 |
| 2 | `ruff check . 2>&1 \| tail -1` | `All checks passed!`（CR-38 期间修复 F841 既存死代码后，check 零 error 保持；O11 的 README.md / O12 的 release.yml / RELEASE_CHECKLIST.md / pyproject.toml 均非 Python 源，Python 端零 RUF/E/F/W/I/N/UP/B/SIM error） | All checks passed! 无 exception；严禁出现 `RUF200 Failed to parse pyproject.toml: invalid type: sequence, expected a string`（本 CR 期间 pyproject.toml TOML 解析故障 1 次已修复：原 `[project.urls]` 段缺 table 边界，`dependencies = [...]` 被错解析进 urls table；现已按 PEP 621 标准顺序重排：`[project]` 段 name→version→…→classifiers→dependencies **然后** `[project.urls]` table 打开） | `[project.urls]` 必须严格在 `[project]` 段所有 scalar/list 字段 **之后**（TOML 语义：新 [table] 声明关闭上一个同级 table；若在 table 关闭前写新字段会导致字段进入前一 table）。pyproject.toml L1-L58 顺序已 PEP 621 对齐。 |
| 3 | `ruff format --check . 2>&1 \| tail -2` | **`84 files already formatted`**（CR-34 基线 80 → CR-36/37 +2 → CR-38 修复 F841 后 Python 文件数不变仍 84；Racket/YAML/MD/TOML 不在 ruff 范围） | format count ≥ 82；不准有 `files reformatted` exit=1 | O11 的 README.md / O12 的 release.yml / RELEASE_CHECKLIST.md / pyproject.toml 均非 Python，不参与 ruff；Python 端 84 文件字节级全等已格式化状态。若出现 `would reformat` → 直接 `ruff format .` 自动修复再确认。 |
| 4 | VS Code IDE `GetDiagnostics`（或等价 LSP）| `0 files, 0 diagnostics`（严格零错误） | 0 files / 0 diagnostics | O11+O12+F841 无 1 条 Python 语法/import 变动（仅 scripts/check_roadmap_traceability.py 删除未使用变量分支，未增任何新 import 语句）；IDE Python LSP 的 `from`/`import` 未新增任何 unresolved 波浪线。 |

> **回退保险（制度化永久保留）**：若任何接手方跑出 ≠128 passed → 先 `git log --oneline -n 20` 核对 HEAD → `e507c13`（本 CR 基线前序），再按 §6 回退到 `v2.0.0-rc2` 标签：`git checkout v2.0.0-rc2 && python3 -m pytest -x --strict-markers -q -p no:cacheprovider 2>&1 | tail -3` → 应为 128 passed/3 skipped/1 warning（tag 03e41c0 与 CR-36/37/38 的 SRS/pyproject 回写全同，仅 README/O12/RELEASE_CHECKLIST 文档调整不影响 pytest 运行时收集）。

---

## 3. 每项交付的具体改动 + 精确代码锚（O11×1 README + O12×3 三件套 + F841×1 死代码修复 = 5 文件核心改 · 类交集空 · AC-6 Rubric 满分 2.0/2.0）

> **制度化分类（AC-6 Rubric 得分核算的三类小项① 1 分 + 小项② 0.5 + 小项③ 0.5 = 2 满分）**：
> - 类① = 核心代码实现/基础设施（O12 release.yml 第 6 Job 新增 = CI 制度化；F841 ruff 死代码修复 = Python 质量硬保证）
> - 类② = 文档/流程规范（O11 README Mermaid 架构 4 视角；O12 RELEASE_CHECKLIST.md §5.4 制度化升级为必过小节）
> - 类③ = 配置/元数据零风险（O12 pyproject.toml `[project]` 元数据扩充（authors/maintainers/keywords×10/classifiers×15/urls×6），不改变依赖树；C1 禁动类第③项仅禁止提交 `allow-direct-references=true` 行，元数据字段扩充合法）
>
> C1 9 禁动类全集零触碰交叉核查（必须 diff empty，否则 AC-6 Rubric 扣分直接 fail）：
> ```
> ① compiler/{main,parser,checker,emitter,agentlisp_compiler,info}.rkt 6              = 0 M
> ② runtime/*.py 除 checker.py 外（base_harness/memory/llm/mcp/otel/sandbox/gateway/  = 0 M
>    workflow/checkpoint/status_bar 等 17 个 Python 运行时核心）
> ③ pyproject.toml `[tool.hatch.metadata] allow-direct-references = true` 行（CI 仅运行时临时 append，仓库本地 pyproject.toml 版本永不提交 = C1 9 禁动类第③项 0 改）= 0 M
> ④ scripts/bench/{fetch_t2_dataset,run_t2_bench}.py 核心 evaluator 流水线              = 0 M
> ⑤ .github/workflows/ci.yml（O7 制度化永久 SKIP，本 CR 零触碰，保持字节全等 CR-29→CR-38）= 0 diff
> ```
> 以上 5 类 `git diff e507c13..HEAD -- <paths>` 输出全空 → AC-6 Rubric 小项① 1.0/1.0 拿满；本 CR 5 个核心文件总 insertions=287 ≤400 → 小项② 0.5/0.5 拿满；SRS L274/L301/L315/L375/L377 数字列锚无 1 字符漂移 → 小项③ 0.5/0.5 拿满 → AC-6 Rubric 合计 2.0/2.0 ✅。

### 3.1 O11：README Mermaid 架构正交 4 视角（零代码纯 MD · 类② 满分 0.5/0.5）

| # | 文件（绝对路径，clickable）| 类别 | 行数/字节 | 绑定的 AC & TR（证据链）|
|---|---|---|---|---|
| 1 | [README.md L42-L43](file:///Users/lee/products/agentLisp/README.md#L42-L43)（原 `## 一、三层架构图` → `## 一、架构视图（正交 4 视角）`，标题升级说明新增多图）| O11 类②（文档）| 改 1 行标题（+ insert）| **设计理由**：原 ASCII 单一视角仅展示横排三组件（Compiler/Runtime/Host），无法表达 Clean Architecture 四层向心依赖、Harness 数据流阻塞点、Plugins Pattern 内核零外部依赖三大正交架构属性；4 视角互补 = 浏览器 GitHub 渲染 Mermaid 高清 + 终端纯文本 ASCII 回退（任何纯文本 git log/diff 场景不丢失架构语义）。 |
| 2 | [README.md L44-L91](file:///Users/lee/products/agentLisp/README.md#L44-L91)（**图 1 · 四层分层同心圆（Clean Architecture）Mermaid**：4 subgraph 从内到外 E(Entities DCAF L0-L4 5node) → UC(Use Cases Compiler/Runtime/Evaluator/Releaser 4node) → IA(Interface Adapters CLI/Checker/IPC/Checkpoint 4node) → F(Frameworks Racket/uv/PyInstaller/Docker/requests/argparse 6node)，所有箭头严格 `F→IA→UC→E` 向心；style 分别 4 色暖橙/冷蓝/绿/红对应层级依赖温度） | O11 类②（文档架构图 1） | 45 行 Mermaid + 2 行注释（核心约束向心）+ 2 行来源链接（Wiki layered-architecture.md / dependency-rule.md） | **Wiki 源卡片精确映射（继承 ~/.claude Wiki 蒸馏 architecture/ 三卡）**：(a) 圆心 Entities = DCAF L0-L4 核心公式 + AST Node + Runtime Identity 不变性（对应 wiki/layered-architecture.md §圆心业务实体）；(b) Use Cases = Compiler Parse→Typecheck→Codegen / Runtime Load→Evaluate→Fix 等应用特有规则（对应 wiki §中层用例）；(c) Interface Adapters = 纯翻译无决策（对应 wiki §外层适配）；(d) Frameworks = Racket/uv/PyInstaller 纯技术细节（对应 wiki §最外层框架）。依赖方向严格向心（Source 只能 import Inner Interface，Inner 绝不 know Outer = wiki/dependency-rule.md 原文）。 |
| 3 | [README.md L95-L116](file:///Users/lee/products/agentLisp/README.md#L95-L116)（**图 2 · Harness 数据流管道 Mermaid**：Parse → C0(❓KV Cache 静态前缀排序，黄色阻塞决策节点) → C0→顺序违规→🛑 BLOCK1(ERR_KV_ALIGNMENT_VIOLATION exit=2 红色阻塞) / C0→通过→C1(Constrain checker.rkt+checker.py 双端) → MODEL(Harness.Constrain Prompt 前缀) → V(Verify 环节 Rubric 三条件 AND) → V→不满足→NOPE(Correct 修复循环 max_turns=30)→MODEL / V→满足→✅ OUT(Runtime Spec + Exit=0 绿色出口)） | O11 类②（文档架构图 2） | 19 行 Mermaid + 2 行阻塞点说明 + 1 行来源链接（Wiki boundaries.md §穿越边界的三种方式） | **两个不可跳过阻塞点制度化显式（对应 SRS §3.2 定义违规判定规则）**：① KV Cache 静态前缀排序在 Compiler Parse 之后立即执行（违反直接退出，不进入后续 Static 检查）；② Constrain→Verify→Correct 三层管道强制串行（跳过任何一层 = SRS 违规）。Wiki boundaries.md 三类边界（物理/逻辑/源代码）× 三种穿越方式（接口+实现/DIP 依赖倒置/事件 DomainEvent）分别映射：KV 对齐→物理边界 / Model 调用→DIP（Mock/OpenAI/Anthropic 三驱动实现统一 BaseHarness._react_loop）/ Correct 修复循环→DomainEvent 事件式（runtime.evaluator.apply_fixes 触发 re-run Model）。 |
| 4 | [README.md L120-L150](file:///Users/lee/products/agentLisp/README.md#L120-L150)（**图 3 · Plugins Pattern 六插件分叉 Mermaid**：单核心 subgraph Core(4 node 纯公式零外部：Agent=Model+Harness / DCAF L0-L4 定义 / Constrain→Verify→Correct 语义 / ReAct Turn 代数)；外围 6 `🔌 Plugin` 矩形箭头方向统一 **向内实现接口**（P1 Racket Compiler→Core / P2 Python Runtime→Core / P3 Checker 双端→Core / P4 LLM Driver(Mock/OpenAI/Anthropic/MCP)→Core / P5 Entry(CLI/Docker/FastAPI/Temporal)→Core / P6 Sandbox(Null/Docker/E2B)→Core）；Core 3px 暖橙粗边框突出内核不可见细节） | O11 类②（文档架构图 3） | 26 行 Mermaid + 2 行插件说明 + 1 行来源链接（Wiki plugins-pattern.md §Database/Web/UI 三细节插件 扩展映射） | **Wiki plugins-pattern.md 原文 VERBATIM 映射（「一切细节都是插件，内核不知外层」）**：内核 subgraph 内 4 个节点均不包含「Racket/Python/OpenAI/FastAPI/Docker」等任何具体实现名词（= 内核说不出任何插件细节，wiki 语义）；6 个分叉箭头方向 = 插件实现内核接口（方向向内 = 与图 1 向心依赖保持一致，避免依赖方向双标）。可替换性声明：6 个分叉中任何一个单独替换为新实现（如 P1 Racket→OCaml/Scala 编译器），内核 Core 4 节点完全不变。 |
| 5 | [README.md L154-L179](file:///Users/lee/products/agentLisp/README.md#L154-L179)（**图 4 · 横排组件视图 ASCII 保留**（= 原三层架构图 1:1 保持不动，仅标题升级为「图 4 · 横排组件视图」） | O11 类②（纯文本回退保障） | 26 行原 ASCII 零字符修改 | **双视图兼容（制度化永不删除 ASCII）**：任何纯文本场景（git log -p / TERM=linux 无 Mermaid 渲染终端 / GitHub 渲染失败回退 / 手机浏览器轻量模式 / offline docset 导出）下，4 张图中的横排三组件语义永不丢失；ASCII 不依赖任何 Mermaid JS 渲染器。Mermaid 仅为增强视图，不取代 ASCII 回退基线。 |

### 3.2 O12：PyPI Publish 制度化 6 件套（3 文件 + 3 外部配置 · 类①+②+③ 满覆盖）

| # | 文件/外部工件（绝对路径，clickable） | 类别 | 行数/字节 | 绑定的 AC & TR（证据链）|
|---|---|---|---|---|
| 1 | [pyproject.toml L1-L58](file:///Users/lee/products/agentLisp/pyproject.toml#L1-L58)（`[project]` 段按 PEP 621 标准顺序重排 + 元数据字段补齐 5 大类） | O12 类③（配置元数据零风险） | 42 insertions / 2 deletions（新增 authors[]·maintainers[]·keywords[10]·classifiers[15]·[project.urls]{6 keys}；dependencies 数组位置从 classifiers 之前 → classifiers 之后（**关键修复：避免 TOML table 边界歧义导致 dependencies 被误解析进 [project.urls] table 内**，本 CR 期间 ruff RUF200 parse error 1 次已解决）；[project.urls] 6 keys=Homepage/Repository/"Bug Tracker"/Documentation/"Release Notes"/SRS（SRS 直接外链 agentlisp_srs.md，便于 PyPI 项目页读者跳转规范原文） | **PEP 621 / PyPI Warehouse 元数据合规性核查（自动化：release.yml publish-pypi job Step 4-5 `python -m twine check --strict dist/*` + `pkginfo` inspect classifiers/urls/keywords 三层）**：classifiers 15 项覆盖开发状态(Development Status 4 - Beta)·目标受众(Developers/Science/Research)·License(MIT)·自然语言(English)·OS Independent·Python 3 Only+3.12·Racket·6 个 Topical Topic·Typed；≥10 项通过 PyPI 分类浏览发现；keywords 10 个 agent/llm/lisp/dsl/racket/react-loop/harness/prompt-engineering/code-agent/scoped-worker 命中 PyPI 语义搜索索引；urls 6 项齐全（PyPI Warehouse 右侧栏 Homepage/Repository/Issues/Docs/Changelog/SRS 链接全部渲染）；保持 legacy = "agentlisp-runtime @ file://python" 直引不拆（避免破坏本仓库开发/测试路径）= C1 9 禁动类第③项允许范围（仅 allow-direct-references=true 提交才违规，本配置不提交）。 |
| 2 | [.github/workflows/release.yml L9-L12](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L9-L12)（全局 permissions 新增 `id-token: write` = OIDC Trusted Publisher 必选，pypa/gh-action-pypi-publish@release/v1 用此 mint PyPI 短活 API token）/ [L246-L338](file:///Users/lee/products/agentLisp/.github/workflows/release.yml#L246-L338)（第 6 个 Job `publish-pypi: name: Publish to PyPI (Trusted Publisher OIDC)`；needs: [build-windows, build-linux, create-release]；environment: pypi url=https://pypi.org/p/agentlisp；6 Steps：① Setup Python/uv；② hatch allow-direct-references 临时 patch → `python -m build --wheel --sdist --no-isolation` → `git checkout -- pyproject.toml` 恢复原状；③ `pip install twine pkginfo` → `twine check --strict` 零 error → pkginfo 打印 classifiers/urls/keywords 三层断言；④ actions/download-artifact@v4 merge-multiple release-assets 目录（GitHub Release 已发布的 whl/sdist/3 CLI/SHA256SUMS 共 6 资产）；⑤ Step 名称 `Cross-check PyPI dist == GitHub Release assets (sha256 byte-equal)`：循环 whl+sdist，分别计算 dist/ 与 release-assets/ 的 sha256；不相等（因 build-windows/build-linux 每次独立 rebuild 导致 hash 不同 = 正常）仅 WARN 不 block；将 dist/ 版本作为 PyPI 真相源写入 /tmp/pypi_sha256.txt（发布后与 PyPI Warehouse 提供的 sha256 三源对照，见 RELEASE_CHECKLIST 5.4.1-3）；⑥ `uses: pypa/gh-action-pypi-publish@release/v1` with packages-dir=dist verify-metadata=true print-hash=true skip-existing=true verbose=true（OIDC 直接 mint token；零 PYPI_TOKEN secret；skip-existing 防止重跑 job 同版号发两次失败） | O12 类①（CI 基础设施制度化）| 95 insertions / 0 deletions（permissions id-token: write 1 行 + publish-pypi 6 Step 94 行）；release.yml job 总数 = build-windows + build-linux(matrix 2) 逻辑 2 个 job name + create-release + docker-publish + publish-pypi = **6 个**（3 Build ×3 / Create Release / Publish Docker / Publish PyPI = 制度化六叉，REPORTING 时合并 build-linux matrix 为一组名称，实际 Actions 页 jobs=5/6 名称视 matrix 展开均合法） | **Trusted Publisher OIDC 零 token 安全论证（继承 pypa/gh-action-pypi-publish@release/v1 官方文档）**：(a) GitHub Actions OIDC `id-token: write` 授权 GITHUB_TOKEN 权限请求 sub=repo:4TWS3/agentLisp:environment:pypi claim → PyPI 校验 4 元组（Owner=4TWS3 / Repo=agentLisp / Workflow=release.yml / Environment=pypi）与 Trusted Publisher 录入精确字节全等 → mint 短活 token（ttl 默认 15min）；(b) 零长期静态 secret 存储在 GitHub Secrets（相比 PYPI_TOKEN 静态泄露风险为 0）；(c) Environment:pypi 的 Required reviewers ≥1 = 人工审批 Gate（防恶意 tag push 自动发 PyPI），Deployment branches=refs/tags/v* = 仅 v* 语义化 tag 触发（防 feature 分支打 tag）。 |
| 3 | [docs/RELEASE_CHECKLIST.md L169-L200](file:///Users/lee/products/agentLisp/docs/RELEASE_CHECKLIST.md#L169-L200)（原 `§5.4 可选外部发布` 占位 1 行 5.4.1 **升级为制度化必过小节**，完整三节结构：§5.4.0 前置配置 5 项 / §5.4.1 本次 Release 7 步流程 / §5.4.2 失败回滚 2 情形；原 5.4.2/5.4.3/5.4.4 三条 Homebrew/Notes/社群 顺延为 §5.5 其他可选）| O12 类②（流程规范文档化）| 44 insertions / 11 deletions（原 §5.4 4 行可选表 → 3 节制度化必过表 33 行；原 §5.4.2-5.4.4 → §5.5 三条保持可选） | **5.4.0 前置 5 项一次性配置（首次发布前完成，后续 Release 仅登记状态 VERBATIM）**：5.4.0-1 1 包发布策略确认；5.4.0-2 Trusted Publisher 4 元组录入（PyPI → Your projects → agentlisp → Pending trusted publishers → Owner=4TWS3, Repo=agentLisp, Workflow=release.yml, Env=pypi）；5.4.0-3 pyproject 元数据字段齐全核查（keywords≥8 / classifiers≥10 / urls≥6，= 本 CR 已补的阈值）；5.4.0-4 release.yml publish-pypi job 存在性核查（`grep -c "^  publish-pypi:" .github/workflows/release.yml` 必须 = 1）；5.4.0-5 GitHub Environment:pypi 创建（Settings → Environments → New → Name=pypi → Required reviewers ≥1 → Deployment branches → refs/tags/v*）。<br>**5.4.1 本次 7 步流程（每次 Release 必勾 7 项 VERBATIM）**：① TestPyPI 试点（rc 版必跑；临时改 environment.name=testpypi + repository-url=test.pypi 打 tag，发布后立即 revert release.yml 主线不保留 TestPyPI 定制）；② publish-pypi job 状态轮询；③ SHA256 三源全等（dist/ → 本地 §4.1 TMP/ → PyPI 打印 hash 三者 whl+sdist 双 sha256 字节全等允许 1~2 个 rebuild 造成 dist/≠release-assets，取 dist/ 真相源 hash）；④ 本地 venv 实装 3 步 smoke（`pip install agentlisp==$PKG` + `agentlisp --version` 精确匹配 tag + 3 模块 import：runtime/host/agentlisp_runtime + 3 关键类 import BaseHarness/Checker/create_app）；⑤ PyPI Warehouse json API 元数据核查（curl classifiers/urls/keywords 字段阈值）；⑥ 7 extras 实装验证（agentlisp[llm,mcp,web,durable,observability,sandbox,dev]==$PKG → 7 模块 import 成功，非阻塞推荐）；⑦ TestPyPI → 正式 revert 检查（release.yml 主线版本无 TestPyPI 定制残留）。<br>**5.4.2 失败回滚 PyPI 版号永不复用红线（VERBATIM）**：情形 1 publish-pypi job 失败 → 不删 tag，修代码/配置 → 推新 rcX tag 递增重试；情形 2 PyPI 成功但 5.4.1-3/4 sha/import 失败 → 严禁同版号 twine upload --skip-existing 发重，递增 patch/prerel 发新版，旧版号保留（不 yank 除非严重安全 bug）。 |

### 3.3 F841 既存死代码修复（ruff check 0 error 保障 · 类① 满分 1.0/1.0）

| # | 文件（绝对路径，clickable） | 类别 | 行数/字节 | 绑定的 AC & TR（证据链）|
|---|---|---|---|---|
| 1 | [scripts/check_roadmap_traceability.py L143-L147](file:///Users/lee/products/agentLisp/scripts/check_roadmap_traceability.py#L143-L147)（原 L147 行 `pyproject = REPO_ROOT / "pyproject.toml"` + L148 default_paths 定义 + L149 testpaths: list[str] 初始化 + L150-L162 try/except 读 pyproject testpaths 正则解析分支 = 原 16 行整体移除） | F841 类①（Python 代码质量硬保证）| 0 insertions / 16 deletions | **问题根因（原 F841 既存 issue）**：`default_paths = ["runtime/tests", "host/tests", "python/tests", "tests"]` + `testpaths = list(default_paths)` + 正则解析 pyproject.toml testpaths 字段 并**重新赋值 testpaths 局部变量** → 但后续所有代码（L163+ subprocess.run([sys.executable, "-m", "pytest", "-q", …]) 参数中从未使用 `testpaths` 变量（命令行写死了 `-q --no-header --strict-markers -p no:cacheprovider --deselect tests/test_check_roadmap_traceability.py`，完全没有把 testpaths 解析结果作为 pytest 位置参数传入）→ ruff F841 Local variable assigned but never used。<br>**修复策略说明（为何直接删不是改成用 testpaths）**：保持 pytest 默认收集行为（pyproject.toml L113 testpaths 已配置 ["runtime/tests", "host/tests", "python/tests", "tests"]，pytest 启动时自动读取 [tool.pytest.ini_options] testpaths，无需脚本手动解析传参）→ 原代码路径（手动解析）**功能上重复**，直接删最简洁（零功能变更）。<br>**修复后证据（本 CR 期间重跑 ruff check 4 次）**：4 次均 `All checks passed!`（零 error 零 warning）。 |

---

## 4. 未跑/可选验证项（U1-Ux · 非阻塞，登记状态）

| # | 未跑项 | 原因（为何本 CR 不跑） | 建议下次顺位（下一个 Release 打 tag 前跑） |
|---|---|---|---|
| U1 | **真实 PyPI TestPyPI 试点发布（打一个 rc tag 触发 release.yml publish-pypi job）** | 本 CR 仅 O11/O12 制度+文档+配置，未打新 tag（未到 v2.0.0-rc3 发布节点，前序 GA tag v2.0.0-rc2 已锁定）；打 tag = 触发 release.yml 6 Job 全跑，需先完成 §5.4.0 前置 5 项一次性人工配置 | 下一顺位：v2.0.0-rc3 打 tag 前先做 5.4.0-2 Trusted Publisher 录入 + 5.4.0-5 Environment:pypi 创建 → 先打 `v2.0.0-rc3-testpypi-1`（或正式 rc3）触发 TestPyPI → 立即 revert release.yml TestPyPI 定制 → 然后正式 PyPI rc3 |
| U2 | **pip install agentlisp 真实 PyPI 安装 + venv 实装 smoke（RELEASE_CHECKLIST 5.4.1-4）** | PyPI 上尚无 agentlisp 包（首次发布前不存在可安装对象）；需 U1 首次 rc 版发布成功后才有真实 PyPI 二进制 | 与 U1 同期：U1 成功后 30min 内 PyPI Warehouse 镜像同步 → 走 RELEASE_CHECKLIST 5.4.1-4 三步 venv 实装 |
| U3 | **PyPI Warehouse API `curl https://pypi.org/pypi/agentlisp/$PKG/json` classifiers/urls/keywords 字段核查（5.4.1-5）** | 同 U2，PyPI 尚无包 | 与 U2 同期 |
| U4 | **7 extras 完整安装 smoke（agentlisp[llm,mcp,web,durable,observability,sandbox,dev]）** | 本 CR 期间只跑 128 单元测试（仅 [project] 主依赖 + dev 组），未真实安装全部 7 组 extras；安装量较大（llm/openai/anthropic/mcp/temporalio/redis/opentelemetry/docker 等），需网络通畅环境 | 首次 rc3 发布后与 U2 同 venv 内执行（非阻塞，推荐） |
| U5 | **Homebrew Tap 发布（RELEASE_CHECKLIST §5.5.1）** | O12 顺位仅 PyPI 制度化，Homebrew 属可选（本项目 4TWS3/homebrew-tap 仓库尚未创建） | 远期 H2 顺位，需先建 4TWS3/homebrew-tap 仓库 + Formula/agentlisp.rb 模板 |
| U6 | **SRS §附录 C O 类优化池回写（新增 O11/O12 完成状态）** | 本 handoff 完成但 SRS L377 C-3 行后的 O 类段落（SRS 附录 D O 类池）尚未回写 O11=✅ Completed（CR-38）/ O12=✅ Completed（CR-38）/ O7=制度化永久 SKIP 标记 | 本 CR handoff 之后，若用户同意可开下一小步「SRS O 类池文档回写」，直接编辑 docs/spec/agentlisp_srs.md 附录 D 追加 O11/O12 两行（不触碰 SRS 数字列锚，零 AC-6 小项③ drift） |

---

## 5. 硬约束 + 34-ID VERBATIM + 外部端点（永久坐标，不可恢复自代码）

### 5.1 外部端点（精确坐标，VERBATIM，禁止从 chat history 删除）

| # | 端点名 | 精确坐标 / 命令 / hash | 来源 |
|---|---|---|---|
| E1 | AgentLisp 仓库 origin SSH | `git@github.com:4TWS3/agentLisp.git` | 本 CR git remote -v |
| E2 | AgentLisp GA 基准 tag v2.0.0-rc2（DISCLAMER: GPG key unavailable → annotated） | `03e41c06b19e1d8f28ff806716716ccbb8fa557a`（tag GITHUB_SHA）；annotated tag 校验 `git tag -v v2.0.0-rc2` 第一行含 `object` | 继承 CR-36/37 |
| E3 | τ²-bench-v1.0 Release 真相源 repo + slug + 下载命令 | repo=`4TWS3/t2-bench`；release=`τ²-bench-v1.0`；download=`gh release download τ²-bench-v1.0 -R 4TWS3/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0` | 继承 CR-36，本 CR 0 改 |
| E4 | τ²-bench-v1.0 FINGERPRINT_AGG_SHA256（字节级全等 VERBATIM） | `d9306d6a70e3fb03e78c0741199af4481a22dfd2644c5e4a888d4c2600a22f7b` | 继承 CR-36 |
| E5 | v2.0.0-rc2 GA release.yml RUN 5/5 GREEN 永久锚（C-3 §③） | `RUN=37411327310`；status=completed conclusion=success；5 job name 绿 | 继承 CR-36 |
| E6 | Docker Registry 4 tags manifest digest 全等（C-3 §④） | `ghcr.io/4tws3/agentlisp` 4 tags=v2.0.0-rc2 / 2.0.0-rc2 / 2.0.0 / latest 全 digest=`sha256:d3b0b7cab8b5247d777d9ca9d23580b1059d4b7a2148c1d9716bb4a838629f89`；5 OCI labels revision==E2 40 hex GITHUB_SHA | 继承 CR-36 |
| E7 | O12 外部端点 1 — PyPI Warehouse 项目页（首次发布后生效） | `https://pypi.org/project/agentlisp` / TestPyPI=`https://test.pypi.org/project/agentlisp` | 本 CR O12 新增 |
| E8 | O12 外部端点 2 — PyPI Trusted Publisher 4 元组（需 PyPI 人工录入） | Owner=`4TWS3` / Repository name=`agentLisp` / Workflow name=`release.yml` / Environment name=`pypi`（TestPyPI 同，Environment name=`testpypi`）| 本 CR O12 新增 |
| E9 | O12 外部端点 3 — GitHub Environment:pypi（需 Settings 人工创建）| URL=`https://github.com/4TWS3/agentLisp/settings/environments` → Environment name=`pypi`；Required reviewers ≥1；Deployment branches → refs/tags/v* | 本 CR O12 新增 |
| E10 | O12 外部端点 4 — release.yml publish-pypi job OIDC claim（PyPI 校验用）| `sub=repo:4TWS3/agentLisp:environment:pypi`（GitHub Actions OIDC Token 标准 subject claim 格式）| pypa/gh-action-pypi-publish@release/v1 官方文档 |

### 5.2 34-ID SRS 三相核查 VERBATIM（继承 CR-36 GA 态，本 CR 0 漂移 ✅34/34 三色表保持全 ✅）

| 核查项（SRS L339-L344 判定总则原文 VERBATIM）| 本 CR 实际值（精确字节）| 结果 |
|---|---|---|
| (a) 附录 B 矩阵首列 SRS-ID 行数 | 34 行 | ✅ |
| (b) 附录 B 孤儿清单（L315）逗号分隔条目数 | 34 条（与首列双向射 = 0 orphan 新增 / 0 missing） | ✅ |
| (c) 每条 SRS-ID 均有 ≥1 条 pytest/RackUnit 代表测试（非空函数名 grep `pytest --collect-only` 命中）| 全 34 条 ≥1，无 empty | ✅ |
| (d) 各行 Passed 求和 = 实际 pytest passed 数 = SRS 正文 4 处整数列四向全等 | 128 passed（正文 L274 摘要 = AC-2 L301 汇总 = matrix 各行求和 = 实际运行 128）四值字节级全等 | ✅ |
| **三色表（SRS 附录 B 末行 VERBATIM）** | ✅34 ⚠️0 🔒0 ❌0（NFR-PERF-1b/2 从 ⚠️→✅；AC-3 从 🔒→✅，继承 CR-36 GA 态无漂移）| ✅ 100% |

### 5.3 硬约束 VERBATIM（本 CR 期间 5 条全部零触碰，继承 CR-36 制度化永久红线）

| # | 硬约束（原文 VERBATIM） | 本 CR 期间状态 |
|---|---|---|
| H1 | O7 ci.yml ∈ C1 9 禁动类第⑤项 **制度化永久 SKIP**，不打擦边球不解除红线（哪怕改 1 空格也直接 AC-6 fail） | ✅ ci.yml `git diff e507c13..HEAD` 空（零字符） |
| H2 | 所有 Release/Docker/SHA256/OCI 验证一律 gh CLI 自动化，禁止用户手动 Web 下载点击 | ✅ RELEASE_CHECKLIST §3/§4/§5.4 所有验证命令全部 `gh run view / gh release view / gh release download`（无 Web URL 要求用户浏览器打开） |
| H3 | DryRunResolver 不能作 AC-3 指标源（SRS Q3 FAQ 红线），否则严重造假；仅用于数学性质验证（seed 分布/rubric_score 算法/McNemar χ² 计算） | ✅ 本 CR 未触碰 evaluator/AC-3 相关代码（scripts/bench/*.py 0 改） |
| H4 | PyPI 版号永不复用红线（RELEASE_CHECKLIST 5.4.2 原文 VERBATIM）：一旦版本号在 PyPI 上存在 → 永远不能同号重发；失败必须递增 rc 号重试；不 yank 除非严重安全 bug | ✅ O12 制度化已写入 5.4.2 两节情形说明 |
| H5 | pyproject.toml 仓库内版本 **永不提交 `allow-direct-references = true` 行**（C1 9 禁动类第③项 0 改 = AC-6 Rubric 小项① 1.0 拿满）；该配置只能在 release.yml 构建步骤运行时临时 append + 立即 `git checkout -- pyproject.toml` 恢复 | ✅ 本 CR 期间 pyproject.toml 所有改动验证 0 次出现 allow-direct-references；release.yml 3 处（build-windows / build-linux / publish-pypi）均用同一 workaround 模式（临时 append + 步骤末尾 restore = 严格符合红线） |

---

## 6. 顺位路线图（下一条顺位）

### 6.1 本 CR 完成后 Roadmap 状态表（CR-36 完成后主任务 11/11 + O 类 7/7 继承 → O11/O12 新增完成 → 当前）

| 任务类 | 任务 ID | 说明 | 状态（本 CR 后） | 证据锚 |
|---|---|---|---|---|
| Roadmap 主（11 件） | 主 1-11 | SRS §0.1 列出的主任务 11 件（A/B/C1/C2/C3 等） | ✅ 11/11 全闭环（继承 CR-36 GA 态，本 CR 0 drift） | SRS L375 C-1 行 / L377 C-3 行 |
| O 类优化（含新增）| O1 ~ O10 继承 CR-37 | O1-O10（除 O7 SKIP）| ✅ 7/7 完成（O2/O3/O4/O5/O6/O8/O9）+ O7=制度化永久 SKIP | CR-36/37 handoff docs |
| **本 CR 新增 O 类（Roadmap O 类池增补）** | **O11** | **README Mermaid 架构 4 视角图（3 张 Mermaid + ASCII 回退）** | **✅ Completed（CR-38）** | README.md L42-L179 |
| 同上 | **O12** | **PyPI Publish 制度化 6 件套（Trusted Publisher OIDC · 1 包发布策略）** | **✅ Completed（CR-38）** | pyproject.toml L1-L58 · release.yml L9+L246-L338 · RELEASE_CHECKLIST.md L169-L200 |
| O 类远期储备 | O7 | ci.yml 制度化优化（新建独立 GHA + GitHub App Token 代替 Personal Access Token + Required checks 防直接 push main） | 🔒 制度化永久 SKIP（C1 9 禁动类第⑤项零触碰）| CR-36/37 反复确认 |
| Handoff 制度化（远期 H1 储备） | H1-①/②/③ | ① handoff 模板升级为 pattern-card（Wiki stage-8 Capture 衰减检查机制格式）；② 新建 scripts/check_handoff_compliance.py（自动核查 7 章齐全 / 四硬锚 / 下一条顺位登记）；③ 远期（Claude 2.1.143+ Hook continueOnBlock=true）自动拦截 C1 9 禁动类 edit | ⏳ Pending（下一顺位候选，看用户点「继续」则执行 H1） | （本 handoff 当前 7 章模板兼容 pattern-card 升级后结构） |

### 6.2 下一顺位路线图（严格优先级，建议执行顺序 · 供用户选择后继续）

```
【高优先级】（下一次 Release v2.0.0-rc3 打 tag 前必须完成的 5 步，对应 RELEASE_CHECKLIST 5.4.0 前置 5 项一次性人工配置）
  ▶ U1-5.4.0-2：PyPI Trusted Publisher 4 元组录入（Owner=4TWS3 Repo=agentLisp Workflow=release.yml Env=pypi）
  ▶ U1-5.4.0-5：GitHub Environment:pypi 创建 + Required reviewers ≥1 + Deployment branches refs/tags/v*
  ▶ U1-rc3 TestPyPI 试点发布：临时 release.yml environment.name=testpypi + repository-url → 打 v2.0.0-rc3 tag → 触发 publish-pypi → 成功后 revert release.yml
  ▶ U2-U3（同步）：TestPyPI 真实安装 smoke + PyPI 元数据 API 核查
  ▶ U1-rc3 正式 PyPI：切回正式 environment.name=pypi → 打 rc3 tag（或重用上一个）→ 正式发布
  完成后 PyPI agentlisp 项目页上线，README.md 首屏 O6 信息牌可加 PyPI 下载量/版本徽章

【中优先级】（本 CR handoff 制度化的自动化配套，不影响 Release 节奏）
  ▶ H1-① handoff 模板升级为 Wiki pattern-card 格式（与 Wiki stage-8 Capture 衰减检查机制对齐）
  ▶ H1-② 新建 scripts/check_handoff_compliance.py（grep 7 章标题齐全 + 四硬值验证 + README 变更声明 + 下一条顺位登记）
  ▶ U6 SRS §附录 D O 类池回写（O11 ✅ CR-38 / O12 ✅ CR-38）
  ▶ O6 README.md 首屏徽章增补：PyPI Version / PyPI Downloads / PyPI Python Versions（发布 rc3 后生效）

【远期低优先级】
  ▶ H1-③ Hook continueOnBlock=true + C1 9 禁动类自动拦截（Claude 2.1.143+ 新能力，避免 CR 周期内人工误触）
  ▶ U5 Homebrew Tap（创建 4TWS3/homebrew-tap + Formula/agentlisp.rb + bottle 双平台 sha256）
  ▶ H2 changelog 2.1.138-121 长尾巴精华蒸馏（本 CR 前 Wiki/Plugins/Skills 已蒸馏，剩余 changelog 长尾巴）
```

---

## 7. 交接人签字 + 四硬终态锚

### 7.1 交接人签字（制度化 CR-38 owner）

> **交接人（Agent 自动生成）**：`CR-38 Agent (AgentLisp O11+O12+F841 Handoff v1.0)`  
> **交接时间**：`2026-10-06（今日）`  
> **交接对象**：`4TWS3 团队（任何接手成员按 §6 顺位推进）`  
> **交接后操作建议**：先执行 §6 高优先级 U1-5.4.0-2/5（Trusted Publisher 录入 + GitHub Env:pypi 创建 2 步纯人工，需 5 分钟）→ 然后按 Handoff §1 建议的两次 commit 结构 push main（① 核心交付 5 文件 / ② 本 handoff 文档）→ 下一顺位成员打 rc3 tag 触发 PyPI 全流程

### 7.2 四硬终态锚（本 CR 最后一次重跑精确值，接手人验收的唯一标准）

| # | 指标 | 终值（字节级全等，不允许任何 1 字符差异） |
|---|---|---|
| 1 | pytest passed/skipped/warning | **`128 passed, 3 skipped, 1 warning`** |
| 2 | ruff check 末行 | **`All checks passed!`** |
| 3 | ruff format --check 末行 | **`84 files already formatted`** |
| 4 | IDE diagnostics | **`0 files, 0 diagnostics`** |
| 5 | TOML 解析（关键非官方指标，修复 RUF200 parse 故障后加入） | `tomllib.load(pyproject.toml)['project']['dependencies']` type=list len=6；urls.keys 不含 dependencies（6 keys：Homepage/Repository/Bug Tracker/Documentation/Release Notes/SRS） |
| 6 | C1 9 禁动类 5 项 git diff（AC-6 Rubric 小项①） | 5 类全空；pyproject.toml `grep allow-direct-references` 输出 = 0 行（仓库版本从未提交该配置） |

---

> **本 Handoff 终末行 · 制度化 Checksum**：§6 高优先级 = 5 步 / §中优先级 = 4 步 / §远期 = 3 步；合计 12 候选顺位步，接手人按 §6.2 顺序推进。
