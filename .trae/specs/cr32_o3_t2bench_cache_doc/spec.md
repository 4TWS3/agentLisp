# CR-32 O3 τ²-bench v1.0 外部数据集下载+缓存说明文档化（Spec 工件 1/3）

> **类型**：类别 D 可选优化（O 类，不计入 11 项主 Roadmap；不阻塞 C-1 gh 阻塞解除 / C-3 release 打签顺位）
> **背景**：CR-31 O2 已固化 34-ID / 基线 / 32 行的自动化核查。附录 C C-1 顺位 `τ²-bench v1.0 1000 sample` 仍为 gh CLI 外部阻塞；每次 Reviewer 解除阻塞后需手工记忆：下载路径 / samples.jsonl 字段 / 是否有 .fetched.ok 锁 / 默认缓存目录 / 三校验命令 —— 全部记在 chat 历史或 project_memory，缺 SRS 级可追溯 SSOT 说明 → 本 CR 把这 5 段记忆写入 **附录 D** 作为 SRS 一部分，下轮 C-1 直接引用 VERBATIM 命令零成本。
> **基线锁定（非功能 NFR-2 严格基线零增长 O 类合规）**：CR-31 O2 严格基线 = **127 passed / 1 skipped / 1 warning**；本 O3 全文档化交付，**严格基线保持 127**，不准 Δ≠0（0 新增 pytest，若违规 = AC-5 rule FAIL）。

---

## §1 问题 · 用户 · 目标 · 非目标（PUGN）

| 项 | 内容 |
|---|---|
| **Problem（问题）**：每次 C-1 顺位推进，Reviewer 都要查 project_memory / handoff §5 / SRS §6.3 L207~L239 三处拼命令：①下载（gh release download）②加载路径（$HOME/.cache/agentlisp/t2-bench-v1.0）③样本字段（T2Sample 9 字段 + schema）④校验（sha256/行数 1000/jsonl schema）⑤ CI τ²-bench job 配置。三处拼法每次都不一样（缺统一 VERBATIM 命令 = 手工成本 2~3 分钟 / 轮，下轮可能错写路径） |
| **User（用户）**：未来推进 C-1（τ²-bench 1000 sample 真跑）的 Implementer / Reviewer，以及需要判断「为什么 τ²-bench 没跑」的外部审计者 |
| **Goal（目标）**：在 SRS 新增**附录 D（τ²-bench v1.0 数据集下载+缓存说明）** 5 段齐全，下轮 C-1 解除 gh 阻塞后，直接复制附录 D VERBATIM 命令 3 条即可完成缓存有效性校验 + schema 校验 + 行数 1000 硬断言，零记忆成本 |
| **Non-goal（非目标）**：❌ 不下载 τ²-bench v1.0 真实数据集（仍需 gh CLI 解除阻塞，本 CR 不涉及）❌ 不跑 C-1 的 `fix_rate_total ≥ 0.90` 真跑（属于 C-1 独立 CR 范围）❌ 不新增 pytest（严格基线保持 127 零增长；O 类不贡献基线增量，只减少手工）❌ 不修改 `runtime/`、`compiler/`、`host/`、`pyproject.toml`、`Dockerfile`、`release.yml`（AC-6 Rubric 文件范围硬约束）❌ 不触碰 SRS 附录 B / C 的 4 锚数字列 L274 / L301 / L315 / L376（附录 C 类别 D 本 CR T0 已写 in_progress，终验改 Completed，其他不动）|

---

## §2 功能需求（FR）

| # | 标题 | 说明（可验证）| 绑定交付位置 |
|---|---|---|---|
| FR-1 | 附录 D 新建：路径结构段 + samples.jsonl schema 段 + 校验命令段 + CI τ²-bench job 段 + 常见 FAQ 段 = 5 段齐全 | 附录 D 5 段用 `## D.X YYY` 子标题分隔；每段 ≥3 行（非一句话段），每段有 ≥1 VERBATIM 代码块 / 表格，总 insertions ≥ 25 行（保证不是「1 行说明」糊弄，真正减少下轮 Reviewer 成本） | `docs/spec/agentlisp_srs.md` 附录 D（追加在附录 C 末尾之后，SRS.md 当前锚 L399 空 = 插入位置 VERBATIM）|
| FR-2 | samples.jsonl schema 必须与 fetch_t2_dataset.py `T2Sample` dataclass 字段 9+1 完全全等（含顺序 + 类型 + 可选字段说明）| 字段集合必须精确等于 `{sample_id, baseline_a_pass, buggy_code, language, original_failed_tests, required_tools, rubric_hints, patch_hints, metadata}`（9 个字段），字段说明里必须写：① sample_id 格式 = `t2-v1_00001..t2-v1_01000` 补零 5 位 ② baseline_a_pass 是 bool，「baseline A（旧模型 / 无修复）能否通过 failed tests」③ metadata 是开放 dict，允许额外字段；④ fingerprint_sha256() 的 5 字段连接规则 VERBATIM | SRS 附录 D D.2 段，表格 9 行 = T2Sample 9 字段一一对应 |
| FR-3 | 校验命令 3 条 **独立可复现 VERBATIM**（Reviewer 原样 copy-paste 就成功，不许改参数）：① sha256 集合指纹校验（dry-run seed=42 n=1000 → 1000 fingerprint 文件 sha256 单行输出，便于后续真样本对比）；② jsonl schema 10 字段断言（python3 heredoc 对任意 samples.jsonl 逐行断言，缺字段 / 类型错直接 FAIL exit=1）；③行数 1000 硬断言（`wc -l + awk`） | 三条命令必须每条：a) 有前置环境变量 / 路径假设；b) 有预期 exit=0 说明；c) 失败时 exit=1 / stderr 前缀清晰（便于 CI 集成）；其中 ② 必须用 T2Sample 9 字段 + `sample_id 非空 / language ∈ {python,racket,go,javascript,java,ruby,c,cpp,rust}` 允许列表 10 断言 = 10 schema 断言总数 | SRS 附录 D D.3 段，每条命令前后 ≥2 行解释 / 预期说明 |
| FR-4 | CI τ²-bench job 集成说明段写清：继承 ci.yml python-tests 的矩阵模式 / 三 OS 跳过策略 / continue-on-error 灰度规则 / artifacts 上传 retention | 写清 job 名 `t2-bench`（附录 C C-1 已承诺）；条件：① runs-on=ubuntu-latest；② continue-on-error: true 灰度（C-1 初期允许失败）；③ 拉 gh release download 步骤；④ run_t2_bench.py --sample-range 1..1000 --timeout 600s；⑤ artifacts upload report.json / report.md retention=90 天；共 5 小条齐全（每小条缺 = FR-4 不满足） | SRS 附录 D D.4 段，5 小条表格化 |
| FR-5 | FAQ 段 ≥4 个真实会踩坑的问题（基于 fetch_t2_dataset.py GitHubReleaseResolver.lockfile / DryRunResolver 降级等）：① `.fetched.ok` 锁文件损坏了怎么办？② 没装 gh CLI 但有浏览器手动下载了 zip，解包到哪里？③ DryRunResolver 合成样本能当正式 AC-3 指标吗？④ Windows / macOS 下 $HOME/.cache/agentlisp 路径等价是什么？ | FAQ 每条格式标准：**Q**: 问题；**A**: 回答；**Workaround**: VERBATIM 命令 1 条；共 4 条齐全，Workaround 每处是可直接复制的 shell 命令 | SRS 附录 D D.5 段 Q1~Q4 |

---

## §3 非功能需求（NFR · 严格基线零增长文档型 CR 特有）

| # | 标题 | 指标（可验证）|
|---|---|---|
| NFR-1 | **严格 pytest 基线零增长**：CR-31 O2 终值 = `127 passed / 1 skipped / 1 warning` → CR-32 O3 终值必须保持 `127 passed / 1 skipped / 1 warning`，Δ=±0（不准新增 / 删除任何 pytest 用例；若 project 有 drift，必须解释 drift 来源，否则 AC-5 rule 直接 FAIL）| 严格模式 `pytest -x --strict-markers -q -p no:cacheprovider` 尾行整数精确 = 127 / 1 / 1 |
| NFR-2 | SRS 4 锚数字列零触碰：L274 摘要 pytest 124 / L301 AC-2 \|124\|124\|0\| / L315 `34 SRS-ID` 标签 / L376 C-2 四个整数全等 = 124 —— 四行字节全等 CR-31 O2 的 577940a HEAD，不准任何字符改动 | `diff <(git show 577940a:docs/spec/agentlisp_srs.md | sed -n '274p;301p;315p;376p') <(sed -n '274p;301p;315p;376p' docs/spec/agentlisp_srs.md)` 输出空 ✔ |
| NFR-3 | ruff 双绿 + IDE 0 diagnostics 保持：本 CR 只改 SRS.md（纯 Markdown，无 Python），但 ruff 仍应全仓 All checks passed / format 已格式化；IDE GetDiagnostics = 0 files / 0 diagnostics | 与 CR-31 O2 终值一致，不许降级 |
| NFR-4 | **文档可追溯性**：附录 D 每段（D.1~D.5）都要 **双向引用** fetch_t2_dataset.py / run_t2_bench.py 的精确文件与 L 范围（文件级 clickable 链接格式 + L 行号）；不准只写文件名「见 fetch_t2_dataset.py」，必须写 L 范围，下轮 Reviewer 点进去直接跳转 | 例：D.1 → [fetch_t2_dataset.py L33~L35 DEFAULT_CACHE_DIR](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py#L33-L35)；D.2 → [fetch_t2_dataset.py L38~L50 T2Sample](file:///Users/lee/products/agentLisp/scripts/bench/fetch_t2_dataset.py#L38-L50) 等 |
| NFR-5 | **ISO/IEC/IEEE 29148 §5.2 需求唯一性**：附录 D 子标题 D.1~D.5 名在全 SRS 全局唯一；不准与附录 A/B/C 标题重名；附录 D 标题 `## 附录 D τ²-bench v1.0 数据集下载+缓存说明` 在全 SRS grep count=1 | `grep -c '^## 附录 D' docs/spec/agentlisp_srs.md` = 1 ✔（附录 A/B/C 已存在，D 新增，若 E 不存在则 D 是唯一末附录）|

---

## §4 约束 · 依赖 · 假设（CDA）

| # | 类别 | 内容（不可违反，违反直接 Review FAIL）|
|---|---|---|
| **C1** | **硬约束**：**不动** `runtime/`、`compiler/`、`host/`、`pyproject.toml`、`Dockerfile`、`release.yml`、`.github/workflows/ci.yml`、`scripts/bench/*`（只写 SRS.md，零代码改动，AC-6 Rubric 小项 ① 集合同意 ⊆ {SRS.md + .trae/specs/cr32_o3_*/*} 的极小集合） | 违反 C1 → AC-6 Rubric Score ≤1，阈值=2 → 直接 FAIL |
| **C2** | **硬约束**：SRS 4 锚 L274/L301/L315/L376 字节全等 577940a（CR-31 O2 终值）；除类别 D T0 行 in_progress→Completed 外，不准改动附录 B/C 其他任何行的数字、状态、代表列内容 | 违反 C2 → AC-6 Rubric 小项 ③ 0.5 分全扣，Score ≤1.5 → 低于阈值 2 → FAIL |
| **C3** | **硬约束**：本 CR O 类**禁止新增 pytest**（基线零增长）；若任何 `test_*.py` 文件被创建 / 修改，直接 AC-5 rule FAIL + AC-6 小项 ① 文件范围 OOR = 双 FAIL | — |
| **D1** | **依赖**：`T2Sample` dataclass 字段名与顺序 = SRS 附录 D D.2 表格的 ground truth（若未来 t2-bench v1.1 改字段，必须先改 fetch_t2_dataset.py + 再改 SRS 附录 D —— 本次 CR v1.0 字段锁定 VERBATIM 当前 fetch_t2_dataset.py T2Sample = 9 字段）| 见 FR-2 |
| **A1** | **假设**：`DEFAULT_CACHE_DIR = $HOME/.cache/agentlisp/t2-bench-v1.0` 在 macOS / Linux 下都有效；Windows 下 %USERPROFILE%\.cache\agentlisp\t2-bench-v1.0 等价路径在 FAQ D.5 Q4 说明即可，不要求路径统一 | — |
| **A2** | **假设**：CI τ²-bench job（附录 C C-1 末段已写）未来独立 C-1 CR 实现时会引用附录 D D.4 段 5 小条作为 spec 输入，本 CR 不要求 ci.yml 新增 job（遵守 C1）| — |

---

## §5 开放问题 Q1~Q4（全部关闭，不影响 Implement 阶段）

| # | 问题 | 关闭结论（不允许 open question 进入 Implement）| 依据 / 决策理由 |
|---|---|---|---|
| Q1 | D.3 的 sha256 集合指纹命令是「真实数据集」的 sha256 值还是「dry-run 合成样本」的 sha256 值？| **dry-run 合成样本 seed=42 n=1000 的 sha256 值**（真实数据集 sha256 未知，未来 gh 下载后再算；先写 dry-run 指纹，便于下轮 Reviewer 验证「我的 dry-run 行为是否与 CR-32 O3 写的一致，保证 evaluator 三条件 AND 的数学性质不 drift）| 真实数据集 fingerprint_sha256() 的 1000 条 sha256 外部未知；dry-run seed=42 是 project_memory 里的默认值（CR-29 / CR-30 的 AC-3 pytest 2 条都用 seed=42 n=1000 → 1000 条 fingerprint 聚合 sha256 可稳定算出来）|
| Q2 | D.2 schema 段的 10 断言 = 9 字段 + language 允许列表，为什么 10？| 因为 fetch_t2_dataset.py T2Sample 只有 9 字段；但 evaluator 在 run_t2_bench.py 里只接受 `python` 或 `racket` 主语言（8 种允许列表），所以第 10 条断言 = language ∈ 允许列表（未来 t2-bench v1.1 扩语言时，先改 run_t2_bench.py 再改 SRS 附录 D —— 本次 10 断言固定不 变）| 与当前 run_t2_bench.py 的语言分发逻辑一致（project_memory）|
| Q3 | FAQ 段为什么必须 4 条？能不能写 3 条？| **必须 4 条**：锁文件损坏 / 手动下载 zip 路径 / DryRun 能不能当 AC-3 / Windows 路径；3 条会缺一个真实会踩坑（2 个路径坑 + 1 个 AC-3 指标坑 + 1 个平台坑 = 经典 4 坑）；Implement 阶段若写 3 条，按 FR-5 rule FAIL | 减少下轮 Reviewer 踩坑率 ≥95%（每 FAQ = 已踩过的坑）|
| Q4 | 附录 D 标题 `## 附录 D ...` 编号是在最后吗？会不会有附录 E？| 当前项目 SRS 附录 = A/B/C 三个（§2 术语表 / §附录 B 矩阵 / §附录 C Roadmap）；CR-32 O3 新增 **附录 D** 就是最新末附录；未来若再有附录 E 规格文档 CR，会在类别 D 追加 O4 行 + 附录 E；本次不考虑 E | NFR-5 唯一性 1 ✔ 保证不会重名 |

---

## §6 验收标准（Acceptance Criteria · 5 rule + 2 rubric = 7 AC，AC-6 唯一 rubric 阈值=2）

### §6.1 AC 明细（每条独立可复现，不依赖 Implementer stdout）

| AC# | 类型 | 独立复现命令（VERBATIM · Reviewer 原样跑）| 预期结果（PASS 判据）| SRS/NFR 绑定 |
|---|---|---|---|---|
| **AC-1** | `rule` | `awk '/^## 附录 D /{flag=1} /^## / && !/^## 附录 D /{if(flag) exit} flag{print}' docs/spec/agentlisp_srs.md | grep -cE '^### D\.[1-5]' = 5 段齐全（D.1 路径结构 / D.2 schema / D.3 三命令 / D.4 CI job / D.5 FAQ）；每段行数 ≥3（非一句话）；D.1~D.5 每段至少有 ≥1 个 ``` 代码块或 Markdown 表格 | FR-1 5 段齐全 + 非空 |
| **AC-2** | `rule` | D.2 schema 表格 9 行字段 与 `T2Sample` 9 字段全等验证：① `python3 -c "from scripts.bench.fetch_t2_dataset import T2Sample; import dataclasses; print('\n'.join(f.name for f in dataclasses.fields(T2Sample)))"`（按 dataclasses 顺序输出 9 字段名）；② `grep -A 12 'D.2 samples.jsonl Schema' docs/spec/agentlisp_srs.md | grep -oE 'sample_id|baseline_a_pass|buggy_code|language|original_failed_tests|required_tools|rubric_hints|patch_hints|metadata' | sort -u | wc -l` | ① stdout 9 行字段名（按 dataclasses 顺序）与 D.2 表格首列 **9 字段名全集 100% 全等**（sort -u 后 diff 空）；② wc -l = 9（正好 9，不准 8 或 10）；③ D.2 段中必须出现「fingerprint_sha256」的 5 字段连接规则 VERBATIM 字符串 ≥1 次 | FR-2 schema 全等 + fingerprint 说明 |
| **AC-3** | `rule` | 验证 D.3 三校验命令齐全 + 独立可跑（前两条命令本地无真实数据也能跑通 dry-run；第三条行数断言先用 dry-run 输出 samples.jsonl 模拟）：① dry-run 1000 fingerprint 聚合 sha256 单行输出 exit=0；② 10 字段 schema 断言脚本对 dry-run samples.jsonl 跑通 exit=0；③ wc -l 1000 行断言 exit=0；三条命令在 D.3 段用 ```bash 代码块包裹，每条命令代码块里必须明确写 `exit=0 预期` | ①/②/③ 三条命令 VERBATIM 在 SRS 附录 D D.3 中都能找到 grep count=1 每条；本地 dry-run 环境下三条命令独立执行都 exit=0 | FR-3 三校验命令 VERBATIM + 独立通过 |
| **AC-4** | `rule` | D.4 段 CI τ²-bench job 5 小条齐全验证：`grep -A 25 'D.4 CI τ²-bench' docs/spec/agentlisp_srs.md | grep -cE 'ubuntu-latest|continue-on-error|release download|sample-range 1..1000|timeout 600s|report.json|report.md|retention.*90'` | grep count ≥7（5 小条共 ≥7 个独立关键词命中，每小条至少 1 关键词）；表格行 5 行（5 小条表格 = runs-on / continue-on-error / 拉数据集步骤 / run_t2_bench 步骤 / artifacts 上传），每小条的 PASS 判据列非空 | FR-4 CI τ² job 5 小条齐全 |
| **AC-5** | `rule` | `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider 2>&1 | tail -2` | 尾行 **VERBATIM 包含 `127 passed, 1 skipped, 1 warning`** 三个整数精确（Δ=0 零增长；128/126/124 全 FAIL；NFR-1 严格基线 O 类零增量） | NFR-1 严格基线零增长 |
| **AC-6** | **rubric · 0-2 分 · 阈值=2** | 独立 reviewer 手工核查三类：① `git diff --name-only 577940a`（除 SRS.md T0 in_progress→Completed 改动外，diff 集合**必须 ⊆ {docs/spec/agentlisp_srs.md, .trae/specs/cr32_o3_t2bench_cache_doc/*}**；不准出现 scripts/tests/runtime 任何文件；违反小项 ① 扣 1 分（满分 1）② 总 insertions+deletions（排除 .trae/specs/ 的行数统计）：≤120 → 0.5 分；≤200 → 再 0.5 分（满分 1）③ SRS.md 4 锚点 L274/L301/L315/L376 字节全等 577940a（diff 空）→ 0.5 分；三小项合计：①1.0 + ②1.0 + ③0.5？= 实际 2.0 满分（权重：小项①=1；小项②=0.5；小项③=0.5）| Score = **2/2 满分** → PASS；Score=1.5（违反 1 条小项扣 0.5）→ 需 Remediation；Score≤1（违反 ≥2 条 或 触碰 runtime/compiler/host/pyproject.toml 任一）→ 直接 Review FAIL，退回 Implement | C1 / C2 / C3 硬约束的 rubric 显式化 |
| **AC-7** | `rule` | FAQ D.5 Q1~Q4 齐全验证：`awk '/^#### Q[1-4]\b/{print NR": "$0}' docs/spec/agentlisp_srs.md | wc -l`；每条 FAQ 必须出现：**Q:**（1 次）+ **A:**（1 次）+ **Workaround:**（1 次）+ 至少一段 ```bash / ```sh 代码块（每条 FAQ 都有 workaround VERBATIM） | ① `wc -l` = 4（正好 4 条 Q1/Q2/Q3/Q4）；② 每条 FAQ 中 Q/A/Workaround 三段全出现 count=4×3=12；③ 4 条 FAQ 的 workaround 代码块中 grep `mv .fetched.ok /tmp/`（Q1 锁文件损坏）、`unzip t2-bench-v1.0.zip -d $HOME/.cache/agentlisp/t2-bench-v1.0`（Q2 手动解包）、`DryRunResolver(..., seed=42)`（Q3 dry-run 说明）、`%USERPROFILE%\.cache\agentlisp\t2-bench-v1.0`（Q4 Windows 路径）四关键词各出现 ≥1 次（保证内容不是随便写的 FAQ，是真坑）| FR-5 FAQ 4 条齐全 + Workaround 针对性 |

### §6.2 非法构造边界（O3 文档 CR 特有：Implement 阶段必须避免的违规写法，Review 时发现直接 Fail Finding）

- ❌ **禁止 FAQ Q3 回答「DryRunResolver 可以当 AC-3 指标」**：正确回答 = 「DryRunResolver 只用于 CI 无外网时验证 evaluator 三条件 AND 的数学性质；真实 AC-3 `fix_rate_total ≥ 0.90` 仍需 gh 下载 τ²-bench v1.0 真样本，任何在 README / Release Note 中宣称 DryRun = AC-3 PASS 的行为都是违规」；否则 AC-7 rule Fail
- ❌ **禁止 D.2 schema 表格写 10 字段**（多加 `fingerprint_sha256` 字段）：fingerprint_sha256() 是 **方法** 不是字段；字段只能 T2Sample 9 字段；否则 AC-2 Fail
- ❌ **禁止 D.3 三命令写「需要真数据集才能跑」作为解释不提供 dry-run 版本**：三条命令必须每条都能在无真实 gh 数据时，通过 DryRunResolver(n=1000, seed=42) 本地独立跑通 exit=0；否则 Reviewer 无法验证 = AC-3 Fail
- ❌ **禁止 D.4 CI job 段写「建议用 runs-on=macos-14」**：根据附录 C C-1 说明 + GitHub runner 成本考虑，τ²-bench 只在 ubuntu-latest 跑（1000 样本 ~20 分钟），macOS runner 成本 10×，不允许；否则 AC-4 Fail（找不到 ubuntu-latest 关键词）

---

## §7 交付物清单（2 类 + T0 制度化 1 类 = 共 3 文件；AC-6 Rubric 的极小集合）

| # | 路径（若不存在 = 直接 FAIL AC-6）| 类别 | AC# 覆盖 |
|---|---|---|---|
| 1 | `docs/spec/agentlisp_srs.md` 追加「### 附录 D：τ²-bench v1.0 数据集下载+缓存说明」+ D.1~D.5 5 段（insertions ≥25 行） | 核心交付（纯文档）| FR-1/2/3/4/5 · AC-1/2/3/4/7 · NFR-5 |
| 2 | `.trae/specs/cr32_o3_t2bench_cache_doc/{spec.md, tasks.md, review.md}` | Spec Mode 制度化三工件（本 spec.md = 工件 1）| — |
| 3 | `docs/spec/agentlisp_srs.md` 类别 D T0 行「CR-32=O3」状态列 in_progress → Completed（本 CR Implement 结束时必改，不准留在 in_progress 提交 handoff）| 制度化 T0 第一写回写（Plan 阶段必做 in_progress，Implement 阶段末尾改 Completed）| AC-6 小项 ③ SRS 只允许类别 D 行状态列改动 |
