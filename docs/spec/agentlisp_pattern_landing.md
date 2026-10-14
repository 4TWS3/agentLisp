# 21 个设计模式落地清单（脚本从代码生成，勿手改）

> 重新生成：`python3 scripts/pattern_landing_report.py`（判据：rc=0 表示 21/21 齐全）。
> 口径：21 = V1 5 个 + V2 16 个，与注册表 21 个模式 kind 一一对应（注册表共 23 = 21 + memory + multi-agent）。
> 运行时口径（唯一真源 runtime/patterns/__init__.py）：契约 21 / 落地 13 / 声明层 8。核对脚本 scripts/check_pattern_consistency.py。
> 每行的「位置」是 `文件:行号`，可直接跳转核对。

| # | 代 | 模式（宏） | kind | 宏定义位置 | 注册表条目 | 夹具 |
|---|---|---|---|---|---|---|
| 1 | V1 | `defreflect-agent` | `reflect` | `compiler/patterns.rkt:169` | `compiler/pattern_registry.rkt:227` | 3 个（defreflect_code_refiner.al） |
| 2 | V1 | `defrouter-agent` | `router` | `compiler/patterns.rkt:211` | `compiler/pattern_registry.rkt:229` | 3 个（defrouter_ops_gateway.al） |
| 3 | V1 | `defchain-agent` | `chain` | `compiler/patterns.rkt:257` | `compiler/pattern_registry.rkt:231` | 3 个（defchain_doc_pipeline.al） |
| 4 | V1 | `defparallel-agent` | `parallel` | `compiler/patterns.rkt:304` | `compiler/pattern_registry.rkt:233` | 3 个（defparallel_multi_search.al） |
| 5 | V1 | `defplanner-agent` | `planner` | `compiler/patterns.rkt:359` | `compiler/pattern_registry.rkt:235` | 3 个（defplanner_deep_researcher.al） |
| 6 | V2 | `defpriority-agent` | `priority` | `compiler/patterns_v2.rkt:122` | `compiler/pattern_registry.rkt:201` | 3 个（priority01_generic_GENERIC.al） |
| 7 | V2 | `defdecomposition-agent` | `decomposition` | `compiler/patterns_v2.rkt:136` | `compiler/pattern_registry.rkt:203` | 3 个（decomp02_generic_GENERIC.al） |
| 8 | V2 | `deffsm-agent` | `fsm` | `compiler/patterns_v2.rkt:150` | `compiler/pattern_registry.rkt:205` | 3 个（fsm03_generic_GENERIC.al） |
| 9 | V2 | `defevaluator-agent` | `evaluator` | `compiler/patterns_v2.rkt:164` | `compiler/pattern_registry.rkt:207` | 3 个（eval04_generic_GENERIC.al） |
| 10 | V2 | `deftopic-model-agent` | `topic-model` | `compiler/patterns_v2.rkt:178` | `compiler/pattern_registry.rkt:209` | 3 个（topic05_generic_GENERIC.al） |
| 11 | V2 | `defdecomposer-agent` | `decomposer` | `compiler/patterns_v2.rkt:192` | `compiler/pattern_registry.rkt:211` | 3 个（decom06_generic_GENERIC.al） |
| 12 | V2 | `defguardrails-safety-agent` | `guardrails-safety` | `compiler/patterns_v2.rkt:206` | `compiler/pattern_registry.rkt:213` | 3 个（guard07_generic_GENERIC.al） |
| 13 | V2 | `defhitl-agent` | `hitl` | `compiler/patterns_v2.rkt:220` | `compiler/pattern_registry.rkt:215` | 3 个（hitl08_generic_GENERIC.al） |
| 14 | V2 | `defexception-agent` | `exception` | `compiler/patterns_v2.rkt:234` | `compiler/pattern_registry.rkt:217` | 3 个（exc09_generic_GENERIC.al） |
| 15 | V2 | `defexploration-agent` | `exploration` | `compiler/patterns_v2.rkt:248` | `compiler/pattern_registry.rkt:219` | 3 个（explore10_generic_GENERIC.al） |
| 16 | V2 | `defrag-agent` | `rag` | `compiler/patterns_v2.rkt:262` | `compiler/pattern_registry.rkt:247` | 3 个（rag15_generic_GENERIC.al） |
| 17 | V2 | `defa2a-agent` | `a2a` | `compiler/patterns_v2.rkt:276` | `compiler/pattern_registry.rkt:249` | 3 个（a2a16_generic_GENERIC.al） |
| 18 | V2 | `defreasoning-agent` | `reasoning` | `compiler/patterns_v2.rkt:290` | `compiler/pattern_registry.rkt:251` | 3 个（reason17_generic_GENERIC.al） |
| 19 | V2 | `deflearning-agent` | `learning` | `compiler/patterns_v2.rkt:304` | `compiler/pattern_registry.rkt:253` | 3 个（learn18_generic_GENERIC.al） |
| 20 | V2 | `defresource-aware-agent` | `resource-aware` | `compiler/patterns_v2.rkt:318` | `compiler/pattern_registry.rkt:255` | 3 个（resrc19_generic_GENERIC.al） |
| 21 | V2 | `defgoal-agent` | `goal-setting` | `compiler/patterns_v2.rkt:332` | `compiler/pattern_registry.rkt:257` | 3 个（goal20_generic_GENERIC.al） |

合计：**21/21** 个模式同时具备「宏定义 + 注册表 kind 条目」；
V2 每个模式另有 3 个场景夹具（HC / GENERIC / REVERSE），共 48 个。

## 规格 BNF 别名（5 个，转发到 V2 实现名）

- `defa2a-server` → `defa2a-agent`（宏定义 compiler/patterns_v2.rkt:353）
- `defapproval-agent` → `defhitl-agent`（宏定义 compiler/patterns_v2.rkt:361）
- `defguarded-agent` → `defguardrails-safety-agent`（宏定义 compiler/patterns_v2.rkt:365）
- `defprioritized-agent` → `defpriority-agent`（宏定义 compiler/patterns_v2.rkt:349）
- `defresilient-agent` → `defexception-agent`（宏定义 compiler/patterns_v2.rkt:357）
