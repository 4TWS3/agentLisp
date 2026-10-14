# P0-1 交底：E2E 红灯三层根因（US-27 第一步）

> 基线：`54243a1` · 日期：2026-10-14
> 范围：`tests/patterns_runtime/test_e2e_compiled_artifact.py`（编译 → 子进程 import 产物 → 断言）
> 结论：主计划的 P0-1 根因判定**不完整**。红灯有三层，只修探针路径不够。

---

## 1. 主计划写的 vs 实测

| 项 | 主计划 P0-1 写 | 实测 |
|---|---|---|
| 根因 | 探针脚本路径（子进程 `sys.path`） | 路径只是第一层。后面还有两层 |
| 修法 | 子进程传 `PYTHONPATH` | 需要，但不充分 |

**证据**：修完 `PYTHONPATH` 后用例仍红。报错由 `ModuleNotFoundError: runtime`
变成 `ValueError: priority 缺少必需键 :criteria`。

---

## 2. 三层根因

| # | 层 | 现象 | 根因 | 位置 |
|---|---|---|---|---|
| 1 | 测试环境 | 无 racket → `FileNotFoundError`；有 racket → `ModuleNotFoundError: runtime` | 用例硬调 `racket`；探针脚本在 tmp 目录，`sys.path[0]` 非仓库根 | `test_e2e_compiled_artifact.py` |
| 2 | 契约（产物） | `priority 缺少必需键 :criteria`（CT-PRIORITY-01 违约） | V2 宏把用户参数只写进 system-prompt；注册表 emitter 只发 markers | `scripts/gen_patterns_v2.py`、`compiler/pattern_registry.rkt` |
| 3 | 运行时 | 产物加载后无模式指令 | 产物 override 了 `build_context`，漏调 `patterns.before_turn` / `order` | `compiler/agentlisp_compiler.rkt` |

**第 3 层最隐蔽**：它只在「编译产物」路径出现。单测手工设 `self.PATTERNS` 时走基类，发现不了。

---

## 3. 修法

| 层 | 改动 | 为什么 |
|---|---|---|
| 1 | racket 解析：PATH 优先，回退 `.racket/bin`，都无则 skip；探针子进程传 `PYTHONPATH=<repo root>` | 与 `tests/test_output_drift.py` 同口径；「产物依赖 runtime 包」是公开合同 |
| 2 | 宏参数进新键 `:params`；编译期只把注册表**声明过且类型相符**的键提升进 `:config` | `:criteria` 能被消费；任意参数（`:policies` 等）保持 prompt-only，不触发未知键错 |
| 3 | 生成的 `build_context` 改为委托 `super().build_context()`（保留可选 trajectory 兼容） | 拼装与模式注入只有基类一处实现 |

**第 2 层的约束**：不能把任意参数直接塞进 `:config`。
显式 `(:config (:typo 1))` 仍必须报错（`test_unknown_config_key_is_checker_error`）。
`registry-emit` 只发 schema 声明的键，按键名字典序输出（不变式 I3：同输入同产物）。

**为什么键与值都要过**：正向夹具有宽松值。`fsm03_hc_HC.al` 写 `:states (idle running done)`（符号），
schema 要 `string-list?`。只按键提升会让这个正向夹具编译失败。
按「键在 schema 且值过谓词」提升，则它保持 prompt-only，编译通过；
而 `:criteria "urgency"`、`:levels 3` 正常提升。

**注册表去重**：`priority` 曾注册两次。旧条目被 V2 静默覆盖，criteria 的 emitter 变死代码。已删旧条目。

---

## 4. 验证（实测命令）

| 项 | 命令 | 结果 |
|---|---|---|
| E2E 用例 | `PATH=.racket/bin:$PATH pytest tests/patterns_runtime/test_e2e_compiled_artifact.py -q --no-cov` | 1 passed。断言含 `criteria=urgency` / `levels=3` 活到上下文（CT-PRIORITY-01） |
| CR-42 语言层 | `pytest tests/test_cr42_pattern_language.py -q --no-cov` | 5 passed |
| 标准判据 | `python3 tools/standards_check.py` | 17 通过 / 0 失败 / 0 跳过 |
| 静态检查 | `ruff check .` | All checks passed |
| 格式 | `ruff format --check tests/ tools/ runtime/ host/ compiler/ scripts/` | 97 files already formatted |
| 通用提升 | `deffsm-agent` 带 `:initial-state`/`:states` + 一个未知键 | rc=0；产物含 initial-state/states；未知键被忽略 |
| 全仓回归 | `PATH=.racket/bin:$PATH pytest -q --no-cov` | 见 §5 |

---

## 5. 全仓回归

| 轮次 | 命令 | 结果 |
|---|---|---|
| 第 1 轮 | `PATH=.racket/bin:$PATH pytest -q --no-cov` | **2 failed, 629 passed, 8 skipped**（171s） |
| 失败项 | `test_compiler_end_to_end.py` 的 `v2-explore10_hc_HC.al` / `v2-fsm03_hc_HC.al` | 参数键名撞 schema，值类型不符 |
| 修法 | 提升加类型判定（键与值都过才提升） | 见 §3 |
| 复跑子集 | 同上两文件 | 27 passed |
| 第 2 轮 | `PATH=.racket/bin:$PATH pytest -q --no-cov` | 见本次提交 §5.1 |

### 5.1 第 3 轮结果（提交前最终）

| 项 | 值 |
|---|---|
| 命令 | `PATH=.racket/bin:$PATH pytest -q --no-cov` |
| 结果 | **631 passed, 8 skipped, 0 failed** |
| 耗时 | 172.63s |
| 对照基线 | 主计划实测：1 failed, 630 passed, 8 skipped |
| 净变化 | 唯一红灯转绿。**无新增失败** |

---

## 6. 副作用与已登记代价

| 项 | 说明 |
|---|---|
| 产物形状变化 | 用 V2 宏的 `.al` 产物 PATTERNS 多出 schema 声明的键；宏展开多出 `:params`。48 个 fixture 已重生成 |
| 未做 | US-27 的 21 条 E2E 只完成 1 条 |
| 已补 | 装 `rackunit-lib` + `compiler-lib` 后，`raco test compiler/tests/` 23 个全绿；两个 Racket 测试的路径/退出码缺陷已修。见 `20261014_us35_commit_gate_handoff.md` |

---

## 7. 新发现（未修，独立缺陷）

`compiler/main.rkt` 的 `safe-dyn` 吞掉现代 emitter 的异常，静默回退旧 emitter。
本轮我误改注册表语法时，编译 rc=0，但产物变成 legacy 形状（`BaseHarness` 而非 `BaseHarnessV2`）。
这违反「失败必须留痕」。

**建议**：现代 emitter 抛错时，非 0 退出并打印原因；不得静默降级。
