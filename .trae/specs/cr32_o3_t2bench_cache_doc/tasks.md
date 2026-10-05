# CR-32 O3 τ²-bench v1.0 数据集下载+缓存说明文档化（Tasks 工件 2/3）

> **关联 spec.md**: `.trae/specs/cr32_o3_t2bench_cache_doc/spec.md`（7 AC：5 rule + 2 rubric（AC-6 阈值=2）
> **串行依赖图**：T1（附录 D 5 段写入） → T2（D.3 三命令本地 dry-run 独立验证） → T3（FAQ 4 条 workaround 命令 4 坑关键词 4 Workaround 各 1 关键词验证） → T4（终验七合一）；**基线锁定：CR-31 O2 终值 127 → 零增长 Δ=±0 精确
> **T0（已完成）**：SRS 类别 D T0 第一写，CR-32=O3 行状态 = in_progress（CR-31 O2 Completed 正下方新行；T4 终验改 Completed）

---

## Task 1：附录 D 落地（SRS.md L399 空行正下方插入「## 附录 D：τ²-bench v1.0 数据集下载+缓存说明 + D.1~D.5 5 段齐全）

- **Status**: pending
- **Priority**: high
- **前置依赖**: T0 已完成
- **AC 覆盖**: AC-1（5 段齐全）/ AC-2（schema 9 字段全等 T2Sample）/ AC-4（CI job 5 小条）/ AC-7（FAQ 4 条）
- **实现范围**: 纯 Markdown，单文件 SRS.md 插入 30~80 行（AC-6 小项 ② ≤120 行得 0.5；≤200 得 0.5；两档合计 1 分；不准超 200 insertions）

### Task-local Test Requirements（TR）槽位（每条 rule 二值可验）
| TR# | 类型 | 验证命令（Implement 完成后填 Actual Value）| 预期 | Actual Value | PASS? |
|---|---|---|---|---|---|
| T1-TR1 | `rule` | `grep -c '^## 附录 D ' docs/spec/agentlisp_srs.md` | =1（全 SRS 唯一末附录；若已存在算通过；不准 0/≥2）| | |
| T1-TR2 | `rule` | `awk '/^## 附录 D /{flag=1} /^## / && !/^## 附录 D /{if(flag) exit} flag{print}' docs/spec/agentlisp_srs.md \| grep -cE '^### D\.[1-5]'` | =5（D.1~D.5 5 段标题齐全，不准 4/6 顺序颠倒可）| | |
| T1-TR3 | `rule` | D.1 至少 1 个代码块 / Markdown 表验证：每段至少 ≥3 行；5 段总行数 ≥25 | 段总行数 ≥25（SRS 插入行数；D.1~D.5 每段 ≥3 行布尔全 True）| | |
| T1-TR4 | `rule` | 字段集合全等（9 字段）T2Sample）：① `python3 -c "from scripts.bench.fetch_t2_dataset import T2Sample; import dataclasses; print(' '.join(f.name for f in dataclasses.fields(T2Sample)))"` 输出 9 字段；② grep D.2 段 9 字段用 `\| **字段** |` 表行 9 行；diff sort 后 diff 空（字段全集完全一致（顺序不严格按 dataclasses 顺序可放宽；全集全等必须 100%）| sort 后两集合全等；diff 空；grep 表行 9 行；三条件全 True）| | |
| T1-TR5 | `rule` | CI τ² job 5 小条：runs-on ubuntu-latest / continue-on-error true / gh release download / sample-range 1..1000 / artifacts report + retention 90 天 = 5 条关键词命中；D.4 段表格 5 行 | 5 行齐全，每行非空；关键词数 ≥7（关键词 ubuntu-latest continue-on-error gh release sample-range timeout report retention 7 个）| | |

---

## Task 2：D.3 三校验命令独立 dry-run 可验证（每条 exit=0 独立）

- **Status**: pending
- **Priority**: high
- **前置依赖**: T1 Completed（D.3 段三命令必须先写入 SRS 才能本地 dry-run 复现验证
- **AC 覆盖**: AC-3（三命令 3/3 VERBATIM 可复现 exit=0
- **实现范围**: 零代码；只有命令复现 + Evidence 填实 tasks.md Actual Value

### Task-local TR 槽位
| TR# | 类型 | 验证命令 | 预期 | Actual Value | PASS? |
|---|---|---|---|---|---|
| T2-TR1 | `rule` | 命令 ① dry-run 1000 条 fingerprint_sha256() 聚合 sha256sum 单行输出（seed=42 n=1000） | exit=0；stdout 恰好 1 行 64 位 hex 字符（sha256 十六进制）| | |
| T2-TR2 | `rule` | 命令 ② 10 字段 schema 断言（9 字段 T2Sample + language ∈ 允许列表 8 种（python racket go javascript java ruby c cpp rust）共 10 断言 | dry-run 合成 samples.jsonl（1000 行）跑通 exit=0；缺字段 / 类型错 / language 不在 9 种 → exit=1，脚本实现后 SRS VERBATIM 命令可直接复制粘贴到下一 C-1 解除阻塞后用 | | |
| T2-TR3 | `rule` | 命令 ③ 行数断言 1000 行 wc -l + awk（>=1000 的精确 断言；dry-run 1000 条合成 samples.jsonl 行数断言 exit=0；行数 !=1000 exit=1 | exit=0；stderr 空；三条命令在 D.3 段三条 bash 代码块包裹，每条命令标注 exit=0 预期字样 | | |
| T2-TR4 | `rule` | 每条 D.3 段每条命令前/后 ≥2 行解释：解释（命令 >解释（每条命令的路径参数 环境假设 / 真样本 vs 合成样本 / 失败时怎么查错指南 | 三段解释都存在，共 6+ 行解释不准一句话就命令堆在一起；grep -c exit=0 预期 3 |

---

## Task 3：D.5 FAQ 4 条 Workaround 4 坑 关键词 各 1 关键词命中

- **Status**: pending
- **Priority**: high
- **前置依赖**: T1 Completed
- **AC 覆盖**: AC-7（FAQ 4 条齐全；每条 Q/A/Workaround 三段齐全；Workaround 四关键词各 1 次）
- **实现范围**: 纯 Markdown FAQ；四条 FAQ Q1~Q4 每条约 6~10 行；合计 30~40 行

### Task-local TR 槽位
| TR# | 类型 | 验证命令 | 预期 | Actual Value | PASS? |
|---|---|---|---|---|---|
| T3-TR1 | `rule` | `awk '/^#### Q[1-4]\b/' docs/spec/agentlisp_srs.md | wc -l` | =4（Q1/Q2/Q3/Q4 恰好 4 条，不准多不准少）| | |
| T3-TR2 | `rule` | FAQ 每条中 **Q:** A:** Workaround:**grep count per FAQ：4×3=12 | 12 次 总出现次数，每条 3 段；不准漏段；若某条缺段 → False）| | |
| T3-TR3 | `rule` | 四坑关键词精确 1：`mv .fetched.ok /tmp/`（Q1 lockfile 损坏）；② `unzip t2-bench-v1.0.zip -d $HOME/.cache/agentlisp/t2-bench-v1.0`（Q2 手动解包）；③ `DryRunResolver(..., seed=42)`（Q3 DryRun 说明）；④ `%USERPROFILE%\.cache\agentlisp\t2-bench-v1.0`（Q4 Windows 路径）| 四条每条 FAQ 的 Workaround 中四条关键词各出现 ≥1 次（4/4 全中；不准漏哪条 → False）| | |

---

## Task 4：终验七合一（T0~T3 全部 Completed；4 TR = 7 AC→Task→TR 覆盖核算；AC-6 Rubric Score=2/2；严格基线 127 零增长；ruff 双绿；IDE 0 diagnostics；34-ID 三集合全等；SRS 4 锚零触碰）

- **Status**: pending
- **Priority**: high
- **前置依赖**: T1 ∧ T2 ∧ T3 Completed（三前置）
- **AC 覆盖**: AC-5（基线 127 零增长）+ AC-6（Rubric Score=2/2）+ NFR-2（4 锚零触碰）+ NFR-3（ruff/IDE 健康）+ T1~T4 全链路覆盖
- **实现范围**: 零代码；纯命令 + TR 槽 Actual Value 填充

### Task-local TR 槽位
| TR# | 类型 | 验证命令 | 预期 | Actual Value | PASS? |
|---|---|---|---|---|---|
| T4-TR1 | `rule` | pytest 严格基线（127/1/1 精确）：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider 2>&1 | tail -2` | 尾行包含`127 passed, 1 skipped, 1 warning` 三个整数精确；Δ=0（不准 126/128/124）| | |
| T4-TR2 | `rule` | ruff 双绿：`ruff check . && ruff format --check . 2>&1 | tail -1` | ruff check：All checks passed!；format：N files already formatted（N≥71（CR-31 终值 71）| | |
| T4-TR3 | `rule` | IDE GetDiagnostics | 0 files 0 diagnostics | | |
| T4-TR4 | `rule` | 34-ID 三集合全等：orphan(L315)=34 body=34 AppB首列=34；并=34 交=34 drift=0 | 三集合全等 drift=0；差集全空；继承 CR-31 O2 终值（34 数精确不变）| | |
| T4-TR5 | `rule` | SRS 4 锚零触碰：`diff <(git show 577940a:docs/spec/agentlisp_srs.md | sed -n '274p;301p;315p;376p') <(sed -n '274p;301p;315p;376p' docs/spec/agentlisp_srs.md) && echo BYTE_EQUAL` | diff 空；4 锚字节全等 CR-31 O2 终值（禁止任何修改；类别 D T0 in_progress → Completed 可改 L399 行不算数字列零触碰 | | |
| T4-TR6 | **rubric · AC-6 Score 核算** | 三小项合计=2/2；①文件范围⊆{SRS.md + .trae 3 工件；② insert+del ≤120（0.5 分）≤200（再 0.5 分）；③ 4 锚零触碰（0.5 分）| Score=2/2 满分 | Score **2.0/2.0 阈值 阈值 ，2 → PASS | | |

---

## Task 5：两次 commit 结构 + push + handoff 7 章全等 + Review 2 Cycle Verdict

- **Status**: pending
- **Priority**: medium（制度化 CR 收尾；不可跳过；O 类 CR 仍必须 7 章全等 handoff 归档；不准例外
- **前置依赖**: T4 Completed（AC-6 2/2）
- **AC 覆盖**: 7/7 AC→5 rule + 2 rubric（AC-6 Score=2/2

### Task-local TR 槽位
| TR# | 类型 | 验证命令 | 预期 | Actual Value | PASS? |
|---|---|---|---|---|---|
| T5-TR1 | `rule` | 两次 commit 结构：第 1 commit = 核心交付（spec/tasks/SRS.md 附录 D）；第 2 commit = handoff hash fill + review TR fill | git log --oneline -3 前两/三条结构合法；git ls-remote origin main HEAD = local HEAD hash 字节全等 | | |
| T5-TR2 | `rule` | handoff 7 章全等：`diff <(grep "^## " docs/handoff/*_cr31_o2_*.md) <(grep "^## " docs/handoff/*_cr32_o3_*.md)` =空（7 章标题全等）| 7 章标题全等制度化） | | |
| T5-TR3 | `rule` | commit body ≥5 AC 全称出现在两次 commit 前 body 中：`git log --format=%B -2 | grep -cE 'AC-[1-7]' ≥5` | count≥5；禁止单行 -m 分词 | | |

---

## 附录：7 AC → Task → TR 映射表（7 AC×≥1TR = 覆盖 100% 覆盖）

| AC# | 类型 | 依赖 Task | 映射到 TR | Evidence 来源 |
|---|---|---|---|---|
| AC-1 | rule | T1 | T1-TR1, T1-TR2, T1-TR3 | grep 附录 D count=1；D.1~5 5 段；每段≥3 行 ≥25 总 |
| AC-2 | rule | T1 | T1-TR4 | T2Sample 9 字段 dataclasses；D.2 表 9 字段；字节全等 diff 空 |
| AC-3 | rule | T2 | T2-TR1, T2-TR2, T2-TR3, T2-TR4 | 三命令 dry-run exit=0；每条命令前/后≥2 行解释 |
| AC-4 | rule | T1 | T1-TR5 | CI τ² job 5 小条；5 行表格 ≥7 关键词命中 |
| AC-5 | rule | T4 | T4-TR1 | pytest 127/1/1 精确 Δ=0 零增长 |
| **AC-6** | **rubric 阈值=2** | T4 | T4-TR6（Score 核算）+ T4-TR5（SRS 锚零触碰 | 三小项（范围/行数/锚零触 2/2 满分）|
| AC-7 | rule | T3 | T3-TR1, T3-TR2, T3-TR3 | FAQ 4 条 Q/A/Workaround 三段；4 坑关键词各≥1 次 |

**覆盖核算**: 7 AC × (≥1 TR) = 7/7 全覆盖，空集=0 → Gate Pass。
