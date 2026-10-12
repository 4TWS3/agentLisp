# 21 个设计模式落地清单（脚本从代码生成，勿手改）

> 重新生成：`python3 scripts/pattern_landing_report.py`（判据：rc=0 表示 21/21 齐全）。
> 口径：21 = V1 5 个 + V2 16 个，与注册表 21 个模式 kind 一一对应（注册表共 23 = 21 + memory + multi-agent）。
> 每行的「位置」是 `文件:行号`，可直接跳转核对。

| # | 代 | 模式（宏） | kind | 宏定义位置 | 注册表条目 | 夹具 |
|---|---|---|---|---|---|---|
| 1 | V1 | `defreflect-agent` | `reflect` | `compiler/patterns.rkt:169` | `compiler/pattern_registry.rkt:204` | 3 个（defreflect_code_refiner.al） |
| 2 | V1 | `defrouter-agent` | `router` | `compiler/patterns.rkt:211` | `compiler/pattern_registry.rkt:206` | 3 个（defrouter_ops_gateway.al） |
| 3 | V1 | `defchain-agent` | `chain` | `compiler/patterns.rkt:257` | `compiler/pattern_registry.rkt:208` | 3 个（defchain_doc_pipeline.al） |
| 4 | V1 | `defparallel-agent` | `parallel` | `compiler/patterns.rkt:304` | `compiler/pattern_registry.rkt:210` | 3 个（defparallel_multi_search.al） |
| 5 | V1 | `defplanner-agent` | `planner` | `compiler/patterns.rkt:359` | `compiler/pattern_registry.rkt:212` | 3 个（defplanner_deep_researcher.al） |
| 6 | V2 | `defpriority-agent` | `priority` | `compiler/patterns_v2.rkt:106` | `compiler/pattern_registry.rkt:148` | 3 个（priority01_generic_GENERIC.al） |
| 7 | V2 | `defdecomposition-agent` | `decomposition` | `compiler/patterns_v2.rkt:120` | `compiler/pattern_registry.rkt:180` | 3 个（decomp02_generic_GENERIC.al） |
| 8 | V2 | `deffsm-agent` | `fsm` | `compiler/patterns_v2.rkt:134` | `compiler/pattern_registry.rkt:182` | 3 个（fsm03_generic_GENERIC.al） |
| 9 | V2 | `defevaluator-agent` | `evaluator` | `compiler/patterns_v2.rkt:148` | `compiler/pattern_registry.rkt:184` | 3 个（eval04_generic_GENERIC.al） |
| 10 | V2 | `deftopic-model-agent` | `topic-model` | `compiler/patterns_v2.rkt:162` | `compiler/pattern_registry.rkt:186` | 3 个（topic05_generic_GENERIC.al） |
| 11 | V2 | `defdecomposer-agent` | `decomposer` | `compiler/patterns_v2.rkt:176` | `compiler/pattern_registry.rkt:188` | 3 个（decom06_generic_GENERIC.al） |
| 12 | V2 | `defguardrails-safety-agent` | `guardrails-safety` | `compiler/patterns_v2.rkt:190` | `compiler/pattern_registry.rkt:190` | 3 个（guard07_generic_GENERIC.al） |
| 13 | V2 | `defhitl-agent` | `hitl` | `compiler/patterns_v2.rkt:204` | `compiler/pattern_registry.rkt:192` | 3 个（hitl08_generic_GENERIC.al） |
| 14 | V2 | `defexception-agent` | `exception` | `compiler/patterns_v2.rkt:218` | `compiler/pattern_registry.rkt:194` | 3 个（exc09_generic_GENERIC.al） |
| 15 | V2 | `defexploration-agent` | `exploration` | `compiler/patterns_v2.rkt:232` | `compiler/pattern_registry.rkt:196` | 3 个（explore10_generic_GENERIC.al） |
| 16 | V2 | `defrag-agent` | `rag` | `compiler/patterns_v2.rkt:246` | `compiler/pattern_registry.rkt:224` | 3 个（rag15_generic_GENERIC.al） |
| 17 | V2 | `defa2a-agent` | `a2a` | `compiler/patterns_v2.rkt:260` | `compiler/pattern_registry.rkt:226` | 3 个（a2a16_generic_GENERIC.al） |
| 18 | V2 | `defreasoning-agent` | `reasoning` | `compiler/patterns_v2.rkt:274` | `compiler/pattern_registry.rkt:228` | 3 个（reason17_generic_GENERIC.al） |
| 19 | V2 | `deflearning-agent` | `learning` | `compiler/patterns_v2.rkt:288` | `compiler/pattern_registry.rkt:230` | 3 个（learn18_generic_GENERIC.al） |
| 20 | V2 | `defresource-aware-agent` | `resource-aware` | `compiler/patterns_v2.rkt:302` | `compiler/pattern_registry.rkt:232` | 3 个（resrc19_generic_GENERIC.al） |
| 21 | V2 | `defgoal-agent` | `goal-setting` | `compiler/patterns_v2.rkt:316` | `compiler/pattern_registry.rkt:234` | 3 个（goal20_generic_GENERIC.al） |

合计：**21/21** 个模式同时具备「宏定义 + 注册表 kind 条目」；
V2 每个模式另有 3 个场景夹具（HC / GENERIC / REVERSE），共 48 个。

## 规格 BNF 别名（5 个，转发到 V2 实现名）

- `defa2a-server` → `defa2a-agent`（宏定义 compiler/patterns_v2.rkt:337）
- `defapproval-agent` → `defhitl-agent`（宏定义 compiler/patterns_v2.rkt:345）
- `defguarded-agent` → `defguardrails-safety-agent`（宏定义 compiler/patterns_v2.rkt:349）
- `defprioritized-agent` → `defpriority-agent`（宏定义 compiler/patterns_v2.rkt:333）
- `defresilient-agent` → `defexception-agent`（宏定义 compiler/patterns_v2.rkt:341）
