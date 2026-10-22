# 交接：agentLisp 价值验证与生成回路（2026-10-20）

> 下一个会话从这里开始。读完这一份就能接手。

---

## 0 一句话现状

**agentLisp 的"强制纪律"价值已被验证；"让模型从零生成 .al"实测 0/3，但我自己就是同一个模型且写成了 6 个 agent——差距在条件，不在能力。**

---

## 1 本轮真正被数据支持的结论

| 结论 | 证据 | 强度 |
|---|---|---|
| 编译期校验能拦住结构错误 | 复刻六个 agent 时拦下 4 个真 bug（不可达、环、未声明字段、reducer 误用） | 强 |
| 数据链能接真实系统 | 天玑 OLAP 对拍 422,877.56 一致；知识可见集合 22,134 一致 | 强 |
| 一次性生成 .al 不可行 | 评测集 3 条需求，3 轮重试全败 = 0% | 强（样本小） |
| 模型有能力写 .al | **我自己（deepseek-v4-flash）写成了，但用了数百轮 + 工具** | 强（自证） |
| IR 有产品价值 | 未验证 | 无 |

**关键认知修正**：我曾说"人能学会，所以语言可学"——错。我不是人，是同一个模型。
真正成立的命题是：**同一模型，条件不同，结果不同。**

---

## 2 条件差距（下一步的全部依据）

| 条件 | 我（写成 6 个 agent） | scripts/al_generate.py |
|---|---|---|
| 编译次数 | 数百次 | 3 次 |
| 能读编译器源码 | 能 | 不能 |
| 能读原版 Python 参照 | 能 | 不能 |
| 能读生成的 .py | 能 | 不能 |
| 能跑生成的 .py | 能 | 不能 |
| 上下文 | 完整对话 + 文件系统 | 截断 4000 字目录 |
| 能改工具 | 能 | 不能 |

**结论：不是"会不会"，是"给不给"。

---

## 3 下一步唯一任务

把 al_generate.py 从"一次性函数"改成"有工作区的开发 agent"。

要有四样：

1. 工作区（临时目录，可写可读）
2. 读产物 .py（发现语义错，如 if 分支写反）
3. 跑产物 .py（验证真的能出结果）
4. 20-30 轮（不是 3 轮）

形态：

    for i in range(30):
        src = llm(state)
        write("agent.al", src)
        ok, err = compile("agent.al")
        if not ok:
            state += err          # 已有 42 条修复提示
            continue
        py = read("agent.py")     # ★ 关键
        out = run("agent.py")     # ★ 关键
        if semantic_ok: break
        state += py[:2000] + out

判据（同一套 10 条需求）：

| 结果 | 结论 |
|---|---|
| >= 8/10 | 路线成立，做产品化 |
| 4-7 | 还缺工具，继续补 |
| < 4 | 语言对模型太难 -> 改"模板填空" |
| 0-3（同现在） | 我的成功不可复现，IR 在生成场景不成立 |

**先跑这个，再谈其他任何事。**

---

## 4 已完成的工作（可复用）

### 4.1 语言能力（agentLisp 仓库）

| 能力 | 提交 | 说明 |
|---|---|---|
| 节点体 :body | 06fa3a9 | Lisp -> Python，作者不写 .py |
| :lisp 辅助函数 | 7afb6d2 | 模块级函数 |
| 工具体 define-tool :body | 92de008 | 含 runtime/al_tools.py 注册表 |
| loop/recur | 88f96bf | 绕开 Python 无 TCO |
| 宏 + 卫生宏 | 88f96bf / 09b8dde | binder 自动改名，防捕获 |
| interrupt / fanout | 0ab48e5 | 人工中断、并行扇出 |
| py/call-kw | 13bea51 | 关键字参数（os.makedirs 的坑） |
| 逃逸口可见 | ae3b0dc | :handler 节点编译告警 + escaped 标记 |
| 生成回路骨架 | 316ec5b | 3 轮，只看 stderr |
| 评测集 + 基线 | ae179b9 | **0/3 = 0%** |

### 4.2 DX

| 产物 | 说明 |
|---|---|
| docs/llm/al_catalog.json | 机器可读目录，从编译器生成，漂移即 CI 红 |
| docs/llm/errors.json | 42 条报错提示（原因/怎么改/例子） |
| docs/llm/CHEATSHEET.md | 一页速查 |
| scripts/al_new.py | 5 秒跑通第一个 agent |
| scripts/al_traceback.py | Python traceback -> .al 节点行号 |
| scripts/bench_replicas.py | 六个复刻项目合并回归（6/6 全绿） |

### 4.3 天玑复刻（/Users/lee/products/agentlisp-tianji）

| 层 | 状态 |
|---|---|
| 6 节点纯 .al | 完成 |
| OLAP 真 SQLite | 对拍 422,877.56 一致 |
| 三层知识库 | 经验层 22,134 / 证据层 / 口径层，全接 |
| 知识生效 | A/B 实验：有知识/无知识结论档位不同 |
| 前端 | 真实 React（knowledge-base/web 的 dist） |
| PDF | 原版模块 + /api/export/pdf |
| **阶段判定 stage** | **未完成**：shrink 对上(0.0)，runway 未对(0.0 vs 999.0)，stage 未产出 |

---

## 5 已知未完成

| 项 | 状态 | 说明 |
|---|---|---|
| 天玑 stage 判定 | 半成品 | runway 取 cash 时 period 为 None；应用 TIANJI_PERIOD 环境变量 |
| 六章报告 | 未做 | 按 report_spec.yaml |
| OLAP 从 xlsx 现建 | 未做 | 现在读导出后的 SQLite |
| token 级流式 | 未做 | 现在只到节点级，用户会盯白屏 |
| traceback 语句级行号 | 搁置 | 两轮失败，根因与修法见 20261018_srcloc_line_mapping_findings.md |
| 工具权限体系 | 未做 | 优先级低，等生成路线验证 |

---

## 6 踩过的坑（别再踩）

| # | 坑 | 正确做法 |
|---|---|---|
| 1 | 用 docs.domain 过滤知识 | 必须 chunks.domain（差 2,536 原子） |
| 2 | 整句 LIKE 查知识 | 中文不分词，逐级缩短（整句->6->4->2 字） |
| 3 | 用 LLM 长文本当查询词 | 用 user_request |
| 4 | 猜 DB 列名 | 先 PRAGMA table_info |
| 5 | 自己从月度求和还原 ytd | 原版单期口径，直接取引擎 measures |
| 6 | 改完不验证就提交 | 三次"改了但没生效" |
| 7 | 测试固定 thread_id | 跨测试读旧 checkpoint，clarify 死循环 |
| 8 | 图已结束还在 resume | 看 app.get_state().next 是否为空 |

**通用教训：先跑一条 SQL 看数字，再写代码。** 今天五次返工全是反过来的。

---

## 7 环境

    export PATH="$PWD/.racket/bin:$PATH"      # Racket
    export DEEPSEEK_API_KEY=<key>
    export TIANJI_KB_STAR=天玑                 # 必传，缺了拒绝服务
    export TIANJI_PERIOD=2026-06
    export PYTHONPATH=.                       # 跑 scripts/* 时

门禁：scripts/git-gate.sh（raco test + ruff + pytest，约 4 分钟）。

---

## 8 仓库状态

| 仓库 | HEAD | 测试 |
|---|---|---|
| agentLisp | ae179b9 | 854 passed / 5 skipped |
| agentlisp-tianji | 最新 | 4 passed |
| 六个复刻项目 | — | bench 6/6 全绿 |

---

## 9 下一页会话的第一句话

**跑这个，拿到数字，再谈别的：**

    cd /Users/lee/products/agentLisp
    PYTHONPATH=. python3 scripts/al_eval.py -n 3

当前输出应为 0/3。把它改成工作区形态后再跑，对比变化。

**没有这个对比，任何关于"agentLisp 有没有价值"的说法都是判断，不是数据。**
