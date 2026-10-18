# AgentLisp 设计模式落地 —— 专家评审文件清单

> 结论：**21/21 个设计模式已落地**，证据由脚本从代码生成（可复现，非手工声明）。
> 复核对象：**源码树** @ `main` = `89ff7da`（GitHub `4TWS3/agentLisp`）。
> 本文是评审入口；请连同判据与 CI 记录一起看。

## 0. 先声明「看的是哪一层」（避免层间误判）

| 层 | 含模式实现？ | 说明 |
|---|---|---|
| 源码树 `main` | **是（21/21）** | 本文评审对象 |
| Release `v2.1.0` 的整仓包 `agentlisp-2.1.0.tar.gz` | **是** | 76 个 .rkt，`:pattern` 6 处 / `:evolution` 23 处（已实查） |
| Docker 镜像 `ghcr.io/4tws3/agentlisp:v2.1.0` | **是** | 含 compiler/，构建期自证：编译 .al 并断言 self.PATTERNS |
| Python wheel `agentlisp-2.1.0-py3-none-any.whl` | 否 | 只含运行时（runtime/ + host/ 网关）；编译器不经 PyPI 分发 |
| 规格 §6.1/§6.2 点名的 Python 文件 | **不存在** | `tests/test_pattern_checker.py`、`compiler/transpiler.py` 是**设计草案**，原文标注「未实现」；as-built 转译器是 Racket |

## 1. 清单 A：结论与清单（先看这 3 份）

| # | 文件 | 作用 | 规模 |
|---|---|---|---|
| A1 | `docs/spec/agentlisp_pattern_landing.md` | **21/21 落地清单**：每行给「宏定义 文件:行号 + 注册表条目 文件:行号 + 夹具」 | 21 行数据 + 5 别名 |
| A2 | `scripts/pattern_landing_report.py` | 生成 A1 的脚本（从代码取证）；`rc=0` 即 21/21 | 9.0 KB |
| A3 | `tests/test_pattern_landing.py` | 守护 A1：rc=0 / 不得陈旧（重新生成逐字节一致）/ 21 行 + 5 别名 | 3 用例 |

## 2. 清单 B：模式宏实现（21 个宏的源码）

| # | 文件 | 内容 | 规模 |
|---|---|---|---|
| B1 | `compiler/patterns.rkt` | V1 手写宏 5 个（reflect/router/chain/parallel/planner）+ 语法糖 2 个（defmemory-agent / defmultiagent） | 499 行 |
| B2 | `compiler/patterns_v2.rkt` | V2 宏 21 个 = 16 实现 + 5 规格 BNF 别名（生成物，已提交） | 351 行 |
| B3 | `scripts/gen_patterns_v2.py` | B2 的生成器：`KIND_OF`（16 模式→kind）+ `SPEC_ALIASES`（5 别名） | 26.5 KB |

## 3. 清单 C：注册表与编译链（模式如何进产物）

| # | 文件 | 内容 | 规模 |
|---|---|---|---|
| C1 | `compiler/pattern_registry.rkt` | 23 个 kind 的注册表（21 模式 + `memory` + `multi-agent`）；未知键拒绝 | 266 行 |
| C2 | `compiler/agentlisp_compiler.rkt` | `:pattern` / `:evolution` 两块的 parse + 产物发射（`self.PATTERNS` / `self.EVOLUTION`） | 835 行 |
| C3 | `compiler/checker.rkt` | 模式块与 evolution 的静态检查（`ERR_PATTERN_CONFIG` / `ERR_EVOLUTION_CONFIG`） | 661 行 |
| C4 | `compiler/parser.rkt` + `compiler/emitter.rkt` | 前端解析与 Python 发射 | 173 + 184 行 |
| C5 | `compiler/patterns_checker_v2.rkt` | 旁路校验器（宏名表 / HC 夹具映射 / 8×21 矩阵口径） | 222 行 |

## 4. 清单 D：守卫与门禁（评审可自己跑）

| # | 文件 / 命令 | 判据 |
|---|---|---|
| D1 | `scripts/check_patterns_v2_ast.py` | 48 对夹具 → 合法 Core AST（**48/48**） |
| D2 | `tests/patterns/`（`test_pattern_checker_v2.py` 等） | 134 用例：15 宏 × (HC/GENERIC/REVERSE) + 8×21 矩阵（NFR-PATTERN-01/02） |
| D3 | `tests/test_cr42_*.py` | 模式语言 / kind 覆盖（23）/ evolution / 语法糖 / 别名 / 坑守护 |
| D4 | `tools/standards_check.py` | 16 条工具判据（含 A7 本地==CI、A10 测试目录全覆盖）；`python3 tools/standards_check.py` → rc=0 |
| D5 | `.github/workflows/ci.yml` | CI **7/7 green**（sha `986037e`）：ubuntu + windows 双平台真跑 **356** 用例 |

## 5. 清单 E：规格与证据（口径、边界、历史）

| # | 文件 | 作用 |
|---|---|---|
| E1 | `docs/spec/agentlisp-pattern-macros-tech-spec.md` | 模式技术规格；**§0 为 as-built 口径**，§6.1/§6.2 已标注「设计目标，未实现」 |
| E2 | `docs/spec/agentlisp_srs.md` | SRS + 附录 B 可追溯矩阵（含 14→16 条「工具判据」子表） |
| E3 | `docs/spec/agentlisp_lessons_ledger.md` | 踩坑台账 37 条，每条写「现在靠什么守」 |
| E4 | `tests/patterns/fixtures_v2/`（48）+ `tests/patterns/fixtures/`（12 .al + 7 .expected.rkt） | 夹具语料 |
| E5 | `README.md` | 镜像能力边界 + CLI 开关表 |

## 6. 三条复现命令（专家可直接粘贴）

```bash
git clone --depth 1 git@github.com:4TWS3/agentLisp.git && cd agentLisp
python3 scripts/pattern_landing_report.py      # → 21/21，rc=0
python3 scripts/check_patterns_v2_ast.py       # → PATTERNS V2 AST OK (48/48)
printf '(defpriority-agent s\n  :criteria "urgency"\n  :levels 3)\n' > /tmp/s.al
racket compiler/main.rkt -i /tmp/s.al -o /tmp/s.py && grep -n self.PATTERNS /tmp/s.py
```

## 7. 已知边界（诚实声明，供评审核对）

1. **21 的构成** = V1 5 个 + V2 16 个；另有 5 个规格 BNF **别名**（转发到 V2 实现名，不另计）。
2. 注册表共 **23** 个 kind = 21 模式 + `memory` + `multi-agent`（后两者由语法糖宏使用，不在 21 之列）。
3. 每个模式有**独立宏**；模式语义也可直接用 `(:pattern :kind …)` 块表达（键集合由注册表校验，未知键报错）。
4. Python 侧**没有**模式转译器（转译由 Racket 完成）；规格 §6.1/§6.2 的 Python 文件是设计草案且**不存在**。
5. wheel/sdist **不含**编译器（设计如此，已在文档与判据 A9 写明镜像与整仓包才含编译器）。
6. 编译器尚未单独出可下载发行物（可选后续项）。

## 8. 建议评审的 6 个可判定问题

1. 21 个模式与规格 §3 的对应关系是否完备（多/漏/错配）？
2. 每个模式的 **kind 语义**（键集合与 emit 形状）是否符合规格？
3. V1 手写宏与 V2 生成宏的**职责边界**是否清晰（重复实现？）？
4. `:pattern` 与 `:evolution` 的检查强度是否足够（未知键/缺键/越界）？
5. 三条门禁（AST 闸门 / 8×21 矩阵 / 标记独立断言）是否覆盖了规格的验收条款？
6. 落地清单（A1）的**证据列**是否足以支撑「已落地」结论？
