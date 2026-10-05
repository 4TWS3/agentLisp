# CR-29 B-4 FR-CHECK-2 SSOT 8 项 sideeffect builtin 双端集合全等（Spec Mode 工件 2/3 tasks.md）

- 关联 spec：`.trae/specs/cr29_b4_fr_check2_ssot_8/spec.md`（7 AC：6 rule + 1 rubric，AC-6 阈值=2）
- HEAD 开工基线：`169f1d5`（CR-28 hash fill 归档后，严格基线 123 passed）
- 开工前制度化回写：`docs/spec/agentlisp_srs.md 附录 C L367 B-4 行验收列 Pending → in_progress（CR-29）` ✅
- 严格基线：`pytest passed ∈ {123, 124}`，零回退；**目标 = 124 passed**（Δ+1）

---

## 任务依赖图（T0 → T1 → T2 → T3 → T4 → T5 串行，不可并行）

```
T0（已完成 · 制度化）：回写附录 C B-4 行 Pending → in_progress（CR-29）
  ↓
T1 新建 pytest runtime/tests/test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py
（顶层函数唯一，双路径 zero skip，签名 VERBATIM）
  ↓
T2 附录 B L287 FR-CHECK-2 行 Scenario/Passed：1/1 → 2/2；代表列追加新函数名合并；TODO: B-4 清除；孤儿清单 L316 字节全等
  ↓
T3 附录 C L367 B-4 行 in_progress → ✅ Completed（CR-29）；其他列字节不变
  ↓
T4 终验（T4-TR1 全量 pytest 123→124 Δ+1 / T4-TR2 ruff 双绿 / T4-TR3 GetDiagnostics 0 / T4-TR4 AC-6 Rubric 评分 / T4-TR5 孤儿 34-ID 全等核查）
  ↓
T5 commit -F /tmp/*.txt 制度化 + push origin/main + handoff `docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md` 7 章模板
```

---

## 原子任务清单（5 条主任务 T1~T5 + T0 前置已完成）

### T0（前置 · 制度化 · Status=completed）
- **Status**：completed
- **关联 AC**：spec §3 约束 2「先回写附录 C 再开工」
- **Completion Evidence**：`docs/spec/agentlisp_srs.md L367 验收列尾部 = "in_progress（CR-29）"`，其他 4 列字节不变；`git diff docs/spec/agentlisp_srs.md | grep -E "^[-+]" | grep -v "^[-+][-+][-+]" | grep -v "in_progress\|Pending" | wc -l` = 0 ✅

---

### Task 1：新建 pytest（1 顶层函数，双路径 zero skip 制度化）
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-1（签名+文件名）/ AC-2（双路径 zero skip）/ AC-3（严格基线）
- **实现要点**：
  - 文件名 VERBATIM = `runtime/tests/test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py`
  - 顶层 test_* 函数数 = 1（不允许其他 `def test_` 出现）
  - 装饰器行 VERBATIM：`@pytest.mark.req("FR-CHECK-2")`
  - 签名 VERBATIM：`def test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal(tmp_path: Path) -> None:`
  - 函数体内 注释行 必须 包含 8 项成员清单原文 VERBATIM 作为 reference（`bash, git-push, wget, curl, scp, dd, chmod, sudo`），用于 fail message 对称差 打印 时 对照
  - 路径 A（racket 在 PATH：`shutil.which("racket") is not None`）：
    * 用 `subprocess.run([racket, "-e", f"""(require "{REPO_ROOT}/compiler/checker.rkt") (displayln SIDEEFFECT-BUILTIN-TOOLS)"""])`
    * 真 subprocess 真执行 → 若 rc!=0，**不调用 pytest.skip**；改为 自动回退 到 fallback 分支 抽 Racket 代码文本 8 token 比较（真 assert）
    * rc=0 时 stdout.strip() 分词 `stdout.split()` → `racket_set = set(tokens)`
    * assert len(racket_set) == 8；assert racket_set == python_set（从 `runtime.checker import SIDEEFFECT_BUILTIN_TOOLS` 转 set）
  - 路径 B fallback（racket 不在 PATH，或路径 A rc!=0 回退）：
    * 读 `compiler/checker.rkt L87`，正则 `re.compile(r"^\(define\s+SIDEEFFECT-BUILTIN-TOOLS\s+'\(([^)]*)\)\s*$")` 单行匹配
    * m 非 None → `racket_tokens = m.group(1).split()` → 8 个 token
    * assert len(racket_tokens) == 8
    * python_set = set(SIDEEFFECT_BUILTIN_TOOLS)
    * project_expected = {"bash","git-push","wget","curl","scp","dd","chmod","sudo"}（写死为 8 项，对齐 project_memory 枚举原文）
    * **三向全等**：`assert racket_set == python_set == project_expected`
  - `pytest.skip(` 真调用 次数 = 0（grep 精确 0）
  - 所有临时文件 / 文本文件 **必须写在 tmp_path fixture 目录下 或 直接读源 不写任何非临时文件** → `git status -s examples runtime/checker.py compiler/checker.py docs 2>/dev/null | grep -v "^?? .trae\|^?? docs/spec\|^?? runtime/tests" | wc -l` = 0 不污染业务源

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence（Implement 完填）|
|---|---|---|---|
| T1-TR1 | rule | 文件存在 + ast.parse 无 SyntaxError | |
| T1-TR2 | rule | 文件名 VERBATIM：文件名 `os.path.basename(__file__)` == `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal.py` | |
| T1-TR3 | rule | 顶层函数 2 行（decorator + def）签名 VERBATIM：`grep -E -n "^(@pytest|def test_side)" file | wc -l` == 2；且 decorator 精确包含 `FR-CHECK-2` | |
| T1-TR4 | rule | 真 `pytest.skip(` 调用 = 0（精确 grep 计数） | |
| T1-TR5 | rule | 体内 assert ≥ 4（路径 A ≥2 + 路径 B ≥3 + 三向 ≥1，总 ≥4）：`grep -cE "^\s*assert\s+" file` ≥ 4 | |
| T1-TR6 | rule | 局部 pytest 单跑通过：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider -k 'test_sideeffect_builtin_tools_racket_and_python_ssot'` → passed=1，failed=0 | |
| T1-TR7 | rule | 不污染业务源（git status -s 只出 specs/tests/docs/spec 4 类 untracked/modified，不出现 ` M compiler`、` M runtime/checker.py`、` M ci.yml` 等非允许类）| |

---

### Task 2：附录 B L287 FR-CHECK-2 行 1/1 → 2/2，代表列追加新函数合并；TODO 清除；孤儿清单不动
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-4（附录 B 4 数字列 + 孤儿字节全等）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T2-TR1 | rule | 附录 B L287 4 数字列 VERBATIM = `\| **FR-CHECK-2** \| 2 \| 2 \| 0 \| 0 \|`（右对齐 `---:`）| |
| T2-TR2 | rule | 代表列 = 旧函数 + `, ` + 新函数（新函数名 `` `test_sideeffect_builtin_tools_racket_and_python_ssot_8_items_bitwise_equal` `` ），两函数名 分别用反引号 包；格式同 L299 IF-MCP-1 代表列的 2 函数拼接（逗号分隔 + 各自反引号）| |
| T2-TR3 | rule | `grep -c "TODO: B-4" docs/spec/agentlisp_srs.md` = 0 | |
| T2-TR4 | rule | 孤儿清单 L316 字节全等：`diff <(git show 169f1d5:docs/spec/agentlisp_srs.md | sed -n '316p') <(sed -n '316p' docs/spec/agentlisp_srs.md)` = 空 | |

---

### Task 3：附录 C L367 B-4 行验收列 in_progress（CR-29）→ ✅ Completed（CR-29）
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec §3 约束 2（附录 C 状态闭环）+ spec AC-6 Rubric（忠实范围：SRS.md 只改 2 处：附录 B + 附录 C，不 touch 其他行）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T3-TR1 | rule | L367 验收列尾 = `✅ Completed（CR-29）`（中英文括号一致，CR 编号 = 29，连续）| |
| T3-TR2 | rule | 同一行 其余 4 列（B-4 ID / 缺口 / SRS 绑定 / 交付形态）字节不变：`git diff docs/spec/agentlisp_srs.md | grep -E "^[-+]" | grep -v "^[-+][-+][-+]" | grep -v "Completed\|in_progress" | wc -l` = 0 | |
| T3-TR3 | rule | B-3 行 L366 字节 不变：`sed -n '366p' | shasum` 同 169f1d5 基线 shasum | |

---

### Task 4：终验（T4 自证，为 Independent Reviewer 减负）
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-3（严格基线）/ AC-5（ruff+GetDiagnostics）/ AC-6（Rubric 0-2 阈值 2）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T4-TR1 | rule | 全量 pytest 严格基线：`123 ≤ passed ≤ 124`（目标 124 Δ+1）；`failed=0` | |
| T4-TR2 | rule | ruff check = All checks passed；ruff format --check = N≥56 already formatted（允许 +1 新增 pytest .py 文件） | |
| T4-TR3 | rule | GetDiagnostics = 0 files 0 diagnostics（或工具不可用 记默认 0 通过 文字说明）| |
| T4-TR4 | rubric | 忠实范围 AC-6 Rubric 0-2：git diff 类 = 3（specs 3工件 / runtime/tests pytest1 / SRS.md 2处）；文件总数 ≤5；无 ci.yml / release.yml / docker / compiler / runtime.checker.py 修改；Score=2（满分）≥ 阈值 2。分：低=0（超类或改 release），中=1（3-4 docs/tests/specs），高=2（严格 3 类 ≤5 文件）| |
| T4-TR5 | rule | 孤儿 34-ID 三集合全等（制度化核查）：可写临时 python heredoc（**不持久化成 repo 脚本**，跑后删除）→ 读 §3 FR 正文粗体、附录 B 首列粗体、孤儿清单粗体 → 3 集合并集 = 34，交集 = 34，0 孤儿 | |

---

### Task 5：commit -F 临时文件制度化 + push origin/main + handoff 7章模板
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec §3 约束 3 / 约束 4 + spec AC-7（handoff 7 章制度化全等）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T5-TR1 | rule | commit message 用 `-F /tmp/cr29_commit_msg.txt` 长文；`git log -1 --format=%s%n%n%b HEAD` ≥ 3 行；首行 = `CR-29 B-4 FR-CHECK-2 SSOT 8 项 sideeffect builtin 双端集合全等 pytest（123→124 Δ+1，Spec Mode 7/7 AC PASS）`；无 macOS zsh 长消息分词错误（`commit -m "..."` 禁止 ≥3 行正文）| |
| T5-TR2 | rule | push 成功：`git status` clean；`git rev-parse HEAD` == `git ls-remote origin main | awk '{print $1}'` 字节全等；`git push origin main` exit=0，无冲突 | |
| T5-TR3 | rule | handoff 文档已创建：`docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md` 存在；`diff <(grep "^## " docs/handoff/20261005_cr28_b3_cli_exit_handoff.md) <(grep "^## " docs/handoff/20261005_cr29_b4_fr_check2_ssot_8_handoff.md)` = 空（7 章标题逐字全等 CR-26/27/28/29）| |
| T5-TR4 | rule | handoff 文档 和业务改动 在同一个 or 连续两个 commit push 到 origin/main；`git ls-remote origin main` HEAD 包含该 handoff 文件（其他 agent git pull 就能看到 handoff 直接接手）| |

---

*END OF TASKS.*
