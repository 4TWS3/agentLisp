# CR-28 B-3 IF-CLI-1 CLI exit 6 档编码（Spec Mode 工件 2/3 tasks.md）

- 关联 spec：`.trae/specs/cr28_b3_cli_exit_encoding/spec.md`
- HEAD 开工基线：`7d67a1c`（handoff 归档 push 后，严格基线 122 passed）
- 开工前制度化回写：`docs/spec/agentlisp_srs.md 附录 C L366 B-3 行验收列 Pending → in_progress（CR-28）` 已完成 ✅
- 严格基线：`pytest passed ≥ 122，零回退；本轮目标 = 123 passed`（Δ+1）

---

## 任务依赖图（串行：T1 → T2 → T3 → T4 → T5，不可并行）

```
T1 新建 pytest（改 1 文件：runtime/tests/test_cli_*.py）
  → T2 附录 B IF-CLI-1 行 Scenario=6 Passed=6（改 1 行 L298）
    → T3 附录 C B-3 行 in_progress → ✅ Completed（CR-28）（改 1 行 L366）
      → T4 终验（本地全量 pytest + ruff + GetDiagnostics + AC-7 手审）
        → T5 commit -F /tmp/*.txt + push origin/main + handoff CR-28 文档（制度化）
```

---

## 原子任务清单（5 条，每条 Task-local TR 仅 rule / rubric）

### Task 1：新建 runtime/tests/test_cli_if_cli_1_exit_encoding.py — 1 顶层函数 6 子断言双路径 zero skip
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-1（顶层函数签名）/ AC-2（双路径 zero skip）/ AC-3（严格基线）

| Task-local TR ID | 类型 | 规则 / 分栏（VERBATIM，实现完必须自证通过）| Completion Evidence（实现完填）|
|---|---|---|---|
| T1-TR1 | rule | 文件新建成功：`test -f runtime/tests/test_cli_if_cli_1_exit_encoding.py` = 0，且 `import ast; ast.parse(open(__file__).read())` 无 SyntaxError |  |
| T1-TR2 | rule | 顶层函数唯一且签名 VERBATIM：`grep -E -n "^(def |@pytest.mark.req\(\"IF-CLI-1\"\))" runtime/tests/test_cli_if_cli_1_exit_encoding.py` 输出为 **2 行**（1 decorator + 1 def）且 def 行 = `def test_cli_if_cli_1_all_flags_and_6_exit_code_encoding(tmp_path: Path) -> None:` |  |
| T1-TR3 | rule | 内部 6 子断言 ids：`grep -E -o "exit0_ok_checkonly|exit1_check_fail|exit2_parse_fail|exit3_io_fail|exit_ge4_panic|version_v_flag" runtime/tests/test_cli_if_cli_1_exit_encoding.py | sort -u | wc -l` = 6（6 个标识符都命中） |  |
| T1-TR4 | rule | 双路径 zero skip：`grep -c "pytest.skip" runtime/tests/test_cli_if_cli_1_exit_encoding.py` = 0；且 6 子断言每条体内至少 1 个 `assert` hard（`grep -c "^[[:space:]]*assert " runtime/tests/test_cli_if_cli_1_exit_encoding.py` ≥ 6） |  |
| T1-TR5 | rule | 局部 pytest 单跑通过：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider -k "test_cli_if_cli_1_all_flags_and_6_exit_code_encoding"` → exit=0 且 passed ≥ 1 |  |
| T1-TR6 | rule | 临时 bad 文件不落在 examples/ 里（污染业务样例）：所有 exit=1/2 malformed 样例 **必须** 写 `tmp_path`（fixture 给的）临时文件，路径里必须有 `/tmp/pytest-of-` 或 `private/var`，`git status -s examples/` 空 |  |
| T1-TR7 | rule | pytest decorator 标签大小写敏感：`grep -F '@pytest.mark.req("IF-CLI-1")' runtime/tests/test_cli_if_cli_1_exit_encoding.py` —— 必须逐字节匹配附录 B 首列 ID（不能写成 if-cli-1 或 If-CLI-1） |  |

### Task 2：附录 B IF-CLI-1 行 L298 Scenario=6 Passed=6 TODO 去标签，代表列填真实函数名
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-4（附录 B 4 数字列 + 孤儿）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T2-TR1 | rule | 附录 B L298 整行 **从左到右** 7 列 VERBATIM 对齐：`\| **IF-CLI-1** \| 6 \| 6 \| 0 \| 0 \| \`test_cli_if_cli_1_all_flags_and_6_exit_code_encoding\` \| [§5.1 IF-CLI-1:L125-L141](file:///Users/lee/products/agentLisp/docs/spec/agentlisp_srs.md#L125-L141)（-i/-o/--check-only/-m/--json-errors/-V/--version；exit 0=ok /1=check/2=parse/3=io/≥4=panic） \|`，分隔线 4 个数字列右对齐 `---:` |  |
| T2-TR2 | rule | TODO 标签清除：`grep -n "TODO: B-3" docs/spec/agentlisp_srs.md | wc -l` = 0 |  |
| T2-TR3 | rule | 孤儿清单 34 ID 不动：`grep -c "IF-CLI-1" docs/spec/agentlisp_srs.md` ≥ 3（正文、附录 B、孤儿清单 3 处，ID 集合全等，数量不变只增不减）|  |
| T2-TR4 | rule | 孤儿清单 L316 行 **正文内容未动**：`sed -n '316p' docs/spec/agentlisp_srs.md | shasum` = 开工基线（`7d67a1c` 时的孤儿清单整行）同 shasum（用 `git show 7d67a1c:docs/spec/agentlisp_srs.md | sed -n '316p' | shasum` 对比，字节全等） |  |

### Task 3：附录 C L366 B-3 行验收列 in_progress(CR-28) → ✅ Completed（CR-28）
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-6（忠实范围 Rubric，C 附录必须回写关闭）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T3-TR1 | rule | L366 验收列尾部必须存在子串：`✅ Completed（CR-28）`（中英文括号一致，CR-XX 连续编号，不允许写成 CR-27 或 CR-29）|  |
| T3-TR2 | rule | 同一行其余 4 列（B-3 ID/缺口/SRS 绑定/交付形态）**字节不变**：`git diff docs/spec/agentlisp_srs.md | grep -E "^[-+]" | grep -v "^[-+][-+][-+]" | grep -v "Completed\|in_progress" | wc -l` = 0（B-3 行除 Status 列外其他列不动） |  |
| T3-TR3 | rule | 类别 B 下一行 **B-4 不动**：`sed -n '367p' docs/spec/agentlisp_srs.md | shasum` = 开工基线 B-4 行 shasum 字节全等 |  |

### Task 4：终验 Review 前置（独立前自证，实现者本地跑通所有 AC TR，为 Reviewer 减负担）
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-3（严格基线 122→123 Δ+1）/ AC-5（ruff 双绿 + GetDiagnostics 0）

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T4-TR1 | rule | 严格基线全量 pytest：`PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true pytest -x --strict-markers -q -p no:cacheprovider 2>&1 \| tail -5` → 第一行 `passed` 数满足 `N in {122, 123}`（Δ+1 目标 123，若 fallback 全过则 123，若本机环境 edge case 则至少 122 0 回退），failed=0 |  |
| T4-TR2 | rule | ruff 双绿：`ruff check . 2>&1 \| tail -3` = "All checks passed!"；`ruff format --check . 2>&1 \| tail -3` = "50 files already formatted"（或新增后 N≥50，允许 +1）|  |
| T4-TR3 | rule | GetDiagnostics 0：`GetDiagnostics`（工具）返回 `0 files 0 diagnostics`，或若工具不可用则 `mypy runtime tests 2>/dev/null`（不强制 mypy 安装，默认 0）|  |
| T4-TR4 | rubric | 忠实范围 AC-6 Rubric 0-2：`git diff --name-only HEAD \| sort -u` 输出文件列表分三类：① `.trae/specs/cr28_b3_cli_exit_encoding/*.md 3 工件` ② `runtime/tests/test_cli_if_cli_1_exit_encoding.py 新建` ③ `docs/spec/agentlisp_srs.md 改 2 处` → 文件总数 = 5（3spec + 1py + 1md），类数 = 3，无 ci.yml/release.yml/Dockerfile → Score=2，阈值≥2，满分通过。分栏证据：低=0（超过 3 类或改 release/ci），中=1（3-4 类但都是 docs/tests/specs 相关），高=2（严格 3 类，总数 ≤ 5） |  |
| T4-TR5 | rule | 孤儿清单 34 ID 集合全等核查（制度化）：`python3 scripts/tests/verify_34_id_set_eq.py`（如不存在则写临时脚本：读 §3 正文粗体、读 附录 B 首列粗体、读 孤儿清单粗体 → 3 集合并集大小 == 34，交集 == 34，0 孤儿）|  |

### Task 5：commit -F 临时文件制度化 + push origin/main + handoff CR-28 7 章模板文档
- **Status**：pending
- **优先级**：high
- **关联 AC**：spec AC-7（制度化 handoff）+ 附录 C 所有制度化约束

| Task-local TR ID | 类型 | 规则 / 分栏 | Completion Evidence |
|---|---|---|---|
| T5-TR1 | rule | commit message 用 `-F /tmp/*.txt`：不能有 `git commit -m "` 含正文 ≥ 3 行的命令；`git log -1 --format=%s%n%n%b HEAD` ≥ 3 行，首行 `CR-28 B-3 IF-CLI-1 CLI exit 6 档编码 pytest（123 Δ+1）`；无 zsh 分词 pathspec 错误历史 |  |
| T5-TR2 | rule | push 成功：`git status` clean + `git rev-parse HEAD` = 远端 `git ls-remote origin main | awk '{print $1}'`（字节全等），`git push origin main` 无冲突且 exit=0 |  |
| T5-TR3 | rule | 制度化 handoff 已落盘：`head -120 docs/handoff/20261005_cr28_b3_cli_exit_handoff.md | grep -c "^## " == 7`；7 章节标题 **逐字全等** 旧 handoff `docs/handoff/20261005_cr27_b2_perf_job_handoff.md` 的 `## 1. Git 状态 / ## 2. 四硬指标基线 / ## 3. 改动精确锚 / ## 4. 未跑完 & 环境阻塞项 & 复现命令 / ## 5. 运行时硬约束 & 依赖（VERBATIM 保留） / ## 6. 下一步方向（严格附录 C Roadmap 顺序，不跳项） / ## 7. 交接标签（可复现 snapshot）`，正文内容不同但结构相同 |  |
| T5-TR4 | rule | handoff 文件也独立 add + commit 到 origin/main（和业务改动同一 commit 或独立下一 commit 都行，但 `git ls-remote origin main` HEAD 必须包含 docs/handoff/20261005_cr28_b3_cli_exit_handoff.md，其他 agent 拉到能看到）|  |

---

*END OF TASKS.*
