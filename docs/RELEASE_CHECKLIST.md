# AgentLisp Release Checklist（制度化打签前核查清单 v1.0）

> **适用范围**：所有正式 Release（v2.0.0 / v2.0.0-rc3 / v2.0.1 / v2.1.0 及后续）。**严禁跳项**；每一项核查完成后必须在右侧方框内手动勾选 `[x]` 或填写精确字节值。禁止凭印象跳过任何一条。
>
> **硬约束红线（所有 Check 违反即禁止打签）**：
> 1. C1 9 禁动类（见 §1.4）必须 `git diff` 全空；
> 2. 四硬指标（§1.1）四项必须一字不差与声明值全等；
> 3. SRS 三相核查（§1.3）必须 ✅34/34 无任何 ❌ 或 🔒；
> 4. AC-3 真 evaluator（§1.5）必须 `ac3_pass=True` 三条件 AND 全达成；
> 5. C-3 顺位锁（§2.1）必须 5 步依次推进，禁止跳步打签。
>
> **上次成功参考（复制 §0 精确锚）**：v2.0.0-rc2 GA = RUN=37411327310 · head_sha=`03e41c06b19e1d8f28ff806716716ccbb8fa557a` · asset_count=6 · Docker digest=`sha256:d3b0b7cab8b5247d777d9ca9d23580b1059d4b7a2148c1d9716bb4a838629f89`。

---

## §0 本次 Release 元信息锚（打签前先填）

| 字段 | 本次 Release 值（精确字节，填写后不再修改） |
|---|---|
| 本次版本号（SemVer，git tag 名） | `v________________`（例：`v2.0.0` / `v2.0.1-rc3`） |
| 打签前本地 HEAD（40 hex 全） | `________________________________________` |
| GPG/Annotated | `[ ] annotated only` / `[ ] GPG signed（需先配 GPG key）` |
| 打签前最后一次成功四硬（§1.1 结果抄录） | pytest=`____ passed / ____ skipped / ____ warning`；ruff check=`________`；ruff format=`____ files`；IDE diag=`____ files` |
| 打签人 GitHub 账号 | `________`（例：`4TWS3`） |
| 打签日期（YYYY-MM-DD） | `__________` |

---

## §1. Pre-Flight（打签前必过 · 共 11 项 · 100% 通过才允许进入 §2）

> 本节所有命令 **必须在本地 macos 终端在仓库根目录执行**；所有退出码必须 `echo $? = 0`；禁止任何 warning 级别的异常。

### 1.1 制度化四硬指标（4 项 · 必须一字不差全等）

| # | 命令 VERBATIM | 预期值（一字不差） | 本次实填（复制实际输出） | 通过？ |
|---|---|---|---|---|
| 1.1.1 | `PYTHONDONTWRITEBYTECODE=1 AGENTLISP_DOCKER_INFRA=true python3 -m pytest -x --strict-markers -q -p no:cacheprovider 2>&1 \| tail -3` | `128 passed, 3 skipped, 1 warning in ____.__s`（passed/skipped/warning 三数字必须 128/3/1，秒数允许浮动） | 实：`________________________________________________________________` | `[ ]` |
| 1.1.2 | `ruff check . 2>&1 \| tail -1` | `All checks passed!` | 实：`___________________` | `[ ]` |
| 1.1.3 | `ruff format --check . 2>&1 \| tail -2` | 第一条含 `files already formatted`；第二条空。格式文件数必须 ≥ 82（随 Python 文件数增长，只允许增加不允许减少） | 实：`_________________` / count=`____` | `[ ]` |
| 1.1.4 | VS Code / LSP `GetDiagnostics`（或等价 `pylsp`） | `0 files, 0 diagnostics`（严格零 unresolved import / 零语法错误） | 实：`____ files / ____ diag` | `[ ]` |

> **失败回退**：若 1.1.1 ≠ 128/3/1 → 执行 `git stash` 回到干净工作区再跑；若仍不对 → `git log --oneline -n 5` 确认 HEAD 是否回退到上一次 GA tag（例：`git checkout v2.0.0-rc2`）。

### 1.2 Git 工作区洁净（1 项）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 1.2.1 | `git status --porcelain` | **空输出（0 行）**。不允许任何 `M` / `??` / `A` 行。若有，先 `git commit` 或 `git stash` 打签。 | 输出行数：`____` | `[ ]` |

### 1.3 SRS 34-ID 三相核查（2 项 · SRS 为唯一 SSOT）

| # | 命令 VERBATIM · 人工核查要点 | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 1.3.1 | **人工核查**：打开 [agentlisp_srs.md §附录 B 矩阵](file:///Users/lee/products/agentLisp/docs/spec/agentLisp_srs.md#L274-L315)：<br>(a) 首列 34 行 ID 数 = 34 条；<br>(b) L315 孤儿清单逗号分割条目数 = 34 条；<br>(c) §1.1.1 的 pytest passed 数 = 128 与 L274 声明值全等；<br>(d) L301 AC-2 汇总行 Scenario/Passed 双列与 L274 整数全等。 | (a)=34 / (b)=34 / (c)=全等 / (d)=全等 | 实：(a)=`__`(b)=`__`(c)=`[ ]全等`(d)=`[ ]全等` | `[ ]` |
| 1.3.2 | 执行自动化三相核查脚本：`python3 scripts/bench/tests/test_traceability_check.py -v 2>&1 \| tail -1`（若脚本不在 → 临时调用 O2 核查：`grep -cE "^\\| FR-[A-Z0-9-]+ \\| docs/spec/agentlisp_srs.md"`，必须 ≥34） | exit=0；最后一行含 `passed`；无 FAIL/ERROR | 实：`____________________` | `[ ]` |

### 1.4 C1 9 禁动类交叉核查（2 项 · AC-6 Rubric 2.0/2.0 底线）

| # | 命令 VERBATIM（必须全部空输出 = 0 改） | 预期值（所有命令空输出） | 本次实填（每条非空 = 直接 FAIL） | 通过？ |
|---|---|---|---|---|
| 1.4.1 | **全量交叉（推荐）**：复制以下 5 行批量执行后检查空：<br>`git diff --stat HEAD 2>&1 \| grep -E "compiler/\\.rkt$" \|\| true`<br>`git diff --stat HEAD 2>&1 \| grep -E "runtime/(?!checker\\.py)[a-z0-9_]+\\.py$" \|\| true`<br>`git diff --stat HEAD 2>&1 \| grep "pyproject.toml" \|\| true`<br>`git diff --stat HEAD 2>&1 \| grep -E "scripts/bench/(fetch_t2_dataset|run_t2_bench)\\.py$" \|\| true`（注：AC-3 配套常量/evaluator 补齐除外，需人工确认不是核心 pipeline）<br>`git diff --stat HEAD 2>&1 \| grep "ci.yml" \|\| true`（**ci.yml = 绝对零改，哪怕 1 空格**） | 5 行输出必须 **全部空** | 空行数：`____ / 5` | `[ ]` |
| 1.4.2 | **精确字节全等核查（对 ci.yml 专用）**：`git show v2.0.0-rc2:.github/workflows/ci.yml \| shasum -a 256 && shasum -a 256 .github/workflows/ci.yml` → **两 hash 必须字符级全等**。其他 4 类同理可查。 | 两 hash 全等（64 hex 字符相同） | 实：hash1=`________________________________` / hash2=`________________________________` / 全等？`[ ]` | `[ ]` |

> **硬失败处理**：若 1.4.1 任一条非空 或 1.4.2 hash 不等 → **禁止打签**；必须新开独立 CR 解除 C1 9 禁动类限制，再重新走 §1→§2→§3→§4 全流程。

### 1.5 AC-3 真 evaluator 三条件全等 AND（2 项 · C-1 解消核查的重跑确认）

> **即使 C-1 已经历史闭环，打签前必须重新本地真跑一次**，防止代码/SRS 回退导致 AC-3 失败。需网络连通（gh auth 已 login）。

| # | 命令 VERBATIM | 预期值（三条 AND 全部 True） | 本次实填 | 通过？ |
|---|---|---|---|---|
| 1.5.1 | **(a) 下载 + 三校验 τ²-bench 真相源**（首次/清缓存后必须跑）：<br>`mkdir -p $HOME/.cache/agentlisp && gh release download τ²-bench-v1.0 -R 4TWS3/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0 --clobber`<br>`cd $HOME/.cache/agentlisp/t2-bench-v1.0 && sha256sum -c SHA256SUMS && cd -` | 第一行 exit=0；第二行输出必须 `2/2 OK （0 mismatch）`；严禁 1/2 OK。 | 实：`sha256sum` 结果=`____ / 2 OK` | `[ ]` |
| 1.5.2 | **(b) 真 evaluator 1000 条本地跑 3 条件**：<br>`PYTHONPATH=scripts/bench python3 scripts/bench/run_t2_bench.py --dataset t2-bench@v1.0 --sample-range 1..1000 --output /tmp/t2_metrics.json --junitxml /tmp/t2_junit.xml --report json 2>&1 \| tail -20`<br>然后三条件硬断言 VERBATIM：<br>`python3 -c "import json; d=json.load(open('/tmp/t2_metrics.json')); print('fix_rate>=0.90:', d['fix_rate']>=0.90, 'mcnemar_p<0.05:', d['mcnemar']['significant_p_lt_005'], 'rubric_mean>=0.80:', d['ac3_cutoffs']['rubric_mean_ge']); print('ac3_pass:', d['ac3_pass'])"`<br>再加 junit 断言：`grep -E 'tests="[0-9]+" failures="[0-9]+"' /tmp/t2_junit.xml \| head -1` | stdout 末行必须 `Overall: PASS (3-condition AND)`；<br>Python 断言 4 行全为 `True` + `ac3_pass: True`；<br>junit 必须 `tests="2" failures="0"` | 实：fix_rate=`____`；mcnemar_p=`____`；rubric_mean=`____`；ac3_pass=`____`；junit tests=`____` failures=`____` | `[ ]` |

---

## §2. Tag & Push（打签阶段 · 共 5 项 = C-3 顺位锁 §①~§⑤ 的第①②步落地）

> **严格按 C-3 顺位锁 5 步推进（SRS §附录 C C-3 行原文 VERBATIM）**：
> ① A/B/C1/C2 全完工 ≥124 → §1 已过
> ② `git tag -a v2.0.0-rc2` → 本节
> ③ release.yml 5 job green → §3
> ④ 5 OCI labels revision==GITHUB_SHA → §3
> ⑤ SHA256SUMS 0 mismatch → §4

### 2.1 C-3 顺位锁推进核查（5 项逐项确认）

| # | 顺位锁步骤 · 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 2.1.1 | **顺位锁 ①**：确认 §1 全部 `[x]`（§1 至少 11 项全勾） | 11/11 ≥ 11 项 → `[x]` | 通过项数：`____ / 11` | `[ ]` |
| 2.1.2 | **顺位锁 ②-1：创建 annotated tag**：<br>`VERSION=v_______; git tag -a "$VERSION" -m "Release $VERSION — AgentLisp: Agent = Model + Harness"`（GPG 可用时加 `-s`）；<br>核查：`git tag -v "$VERSION" 2>&1 \| head -3`（annotated tag 第一行含 `object`） | exit=0；tag 为 annotated/GPG 非 lightweight | 实：tag type=`________`；tag 名=`$VERSION=________` | `[ ]` |
| 2.1.3 | **顺位锁 ②-2：push tag 到 origin main**（同时 push commit + tag，顺序：先 commit push 再 tag push）：<br>`git push origin main && git push origin "$VERSION"` | 两行均为 `Everything up-to-date` 或 `To github.com:4TWS3/agentLisp.git` + `main -> main` / `vX.Y.Z -> vX.Y.Z`；无 `rejected` / `non-fast-forward` | 实：commit push=`____`；tag push=`____` | `[ ]` |
| 2.1.4 | **顺位锁 ②-3：远程 tag 核查**：`gh release view "$VERSION" -R 4TWS3/agentLisp --json tagName,targetCommitish,isDraft 2>&1 \| head -10`（若尚未自动创建 draft → 等 10 秒 release.yml 触发，或确认 tag 存在：`git ls-remote --tags origin \| grep "$VERSION"`） | `tagName=="$VERSION"`；`targetCommitish` = §0 填的 40 hex HEAD 前 7/40 位全等；`isDraft=false`（release.yml 触发后自动 publish） | 实：targetCommitish=`________________________________` / 全等？`[ ]` | `[ ]` |
| 2.1.5 | **顺位锁 ②-4：确认 release.yml 已被 tag push 触发**：<br>`sleep 20 && gh run list -R 4TWS3/agentLisp -w release.yml -L 3 --json status,conclusion,headBranch,displayTitle 2>&1` | 第一条 RUN 的 `status` 为 `in_progress` 或 `queued`；`headBranch` == `refs/tags/$VERSION`（或 displayTitle 含 tag 名） | 实：RUN ID=`________________`；status=`________`；headBranch=`________` | `[ ]` |

---

## §3. CI Build Watch（CI 构建核查 · 共 6 项 = C-3 顺位锁 §③§④）

> **不允许离开直到 6 项全过**；构建时间通常 15~30 分钟（含 PyInstaller 三平台打包 + Docker 多标签推送）。推荐每 5 分钟 `gh run view` 一次。

### 3.1 release.yml 5/5 GREEN（3 项）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 3.1.1 | **5 job 状态轮询**（§2.1.5 拿到的 RUN_ID 填入）：<br>`RUN_ID=________; gh run view "$RUN_ID" -R 4TWS3/agentLisp --json status,conclusion,headSha,name,jobs 2>&1 \| python3 -c "import json,sys; d=json.load(sys.stdin); print('status:',d['status']); print('conclusion:',d['conclusion']); [print(j['name'], '→', j['conclusion']) for j in d['jobs']]; print('headSha:', d['headSha'])"` | `status=completed`；`conclusion=success`；<br>**5 个 job 名 + conclusion=success**：<br>① Build (ubuntu) → success<br>② Build (windows) → success<br>③ Build (macos) → success<br>④ Publish GitHub Release → success<br>⑤ Publish Docker Image → success<br>（job 名顺序可不同但 5 项必须全 success） | 实：job count 绿=`____ / 5`；conclusion=`________`；<br>headSha=`________________________________`（必须 == §0 的 40 hex 全，字节全等） | `[ ]` |
| 3.1.2 | **CI logs 错误零残留**（尤其 Publish Docker Image job 的 metadata-action 段）：<br>`gh run view "$RUN_ID" -R 4TWS3/agentLisp --log-failed 2>&1 \| head -50`（或等价 web UI 打开失败 logs） | **空输出**。严禁任何 `ERROR` / `Fatal` / `exit 1`（偶发 `warning` 允许但需核查） | 实：error 行：`____` 行（应 0） | `[ ]` |
| 3.1.3 | **3 平台 CLI 资产大小合理性（避免 0 B 损坏）**：<br>`VERSION=v_______; gh release view "$VERSION" -R 4TWS3/agentLisp --json assets 2>&1 \| python3 -c "import json,sys; [print(a['name'], a['size']) for a in json.load(sys.stdin)['assets']]"` | 6 项齐全（O5 三保险生效后永久锚 = 6）：<br>① `agentlisp-linux-x86_64` = 23~28 MB<br>② `agentlisp-macos-arm64`（或 x86_64）= 11~14 MB<br>③ `agentlisp-windows-x86_64.exe` = 12~15 MB<br>④ `agentlisp-*.whl` = 130~160 KB<br>⑤ `agentlisp-*.tar.gz` = 380~410 KB<br>⑥ `SHA256SUMS` = 450~550 B<br>**严禁出现裸名 `agentlisp` 或 `agentlisp.exe` duplicate 条目**（= O5 兜底 + O9 清理未生效） | 实：asset_count=`____`（必须 6）；裸名存在？`[ ]否 / [ ]是=FAIL`；<br>各 size：①=`____MB`②=`____MB`③=`____MB`④=`____KB`⑤=`____KB`⑥=`____B` | `[ ]` |

### 3.2 Docker OCI labels + 4 tags 全等（3 项 = C-3 §④）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 3.2.1 | **5 OCI labels 逐字节核查**（从 CI Publish Docker Image job logs 取 metadata-action 输出段，或本地登录后 inspect）：<br>本地验证（需先 `docker login ghcr.io -u 4TWS3 -p $GH_PAT`）：<br>`VERSION=v_______; docker pull ghcr.io/4tws3/agentlisp:$VERSION >/dev/null 2>&1 && docker inspect ghcr.io/4tws3/agentlisp:$VERSION --format '{{json .Config.Labels}}' 2>&1 \| python3 -m json.tool \| grep -E '"org.opencontainers.image.(revision|version|source|title|created)"'` | 5 条 label 全存在：<br>`revision` = §0 / §3.1.1 的 **40 hex GITHUB_SHA 字节级全等**（严禁仅 7 位短 hash）<br>`version` = `$VERSION`（tag 名字符全等）<br>`source` = `https://github.com/4TWS3/agentLisp`<br>`title` = `AgentLisp v2.0 Runtime Image`（非空即可）<br>`created` = 非空 ISO 8601 时间戳 | 实：revision=`________________________________` / 全等 GITHUB_SHA？`[ ]`<br>version=`________` / source=`________` / title 非空？`[ ]` / created 非空？`[ ]` | `[ ]` |
| 3.2.2 | **4 tags manifest digest 全等**（4 个 tag = semver 四形态；本次 tag 不是 GA 时 tag 数可能 2~3，至少 ≥2）：<br>`VERSION=v_______; for t in "$VERSION" "${VERSION#v}" "$(echo "$VERSION" \| cut -d- -f1)" "latest"; do echo "=== ghcr.io/4tws3/agentlisp:$t ==="; docker buildx imagetools inspect ghcr.io/4tws3/agentlisp:$t 2>/dev/null \| grep "Digest:" \| head -1; done` | 所有输出的 `Digest: sha256:________` **64 位 hex 必须完全相同**（单 manifest 复用 = 4 标签指向同一镜像 = 正确）。例：4 行全 = `sha256:d3b0b7ca...89f89` | 实：digest 全同？`[ ]`；不同条目数=`____ / 4` | `[ ]` |
| 3.2.3 | **本地 smoke CLI（docker run version 一致）**：<br>`VERSION=v_______; docker run --rm ghcr.io/4tws3/agentlisp:$VERSION agentlisp --version 2>&1` | stdout 第一行必须含 `agentlisp, version $VERSION`（或 `2.0.0` 大版本号正确）；exit=0 | 实：version 输出=`________________________________`；exit=`____` | `[ ]` |

---

## §4. Post Release（发布后核查 · 共 5 项 = C-3 §⑤ + O9 线上清 duplicate）

> **即使 CI 全绿也必须执行本节**；CI 全绿 ≠ Release 资产可下载 ≠ SHA 正确。

### 4.1 SHA256SUMS 零 mismatch（2 项 = C-3 §⑤）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 4.1.1 | **gh release download 6 资产到临时目录 + 本地校验**（禁止走浏览器，必须走 gh CLI = O5/O9 线上即清的同一真源）：<br>`VERSION=v_______; TMP=$(mktemp -d) && gh release download "$VERSION" -R 4TWS3/agentLisp -D "$TMP" --clobber && cd "$TMP" && ls -la && echo "--- SHA256SUMS content ---" && cat SHA256SUMS` | `ls -la` 行数必须 = 6 资产 + . + .. = 8 行；**严禁裸名 7/9 行**；<br>`SHA256SUMS` 条目数必须 = 5（3 CLI + whl + sdist，不含 SHA256SUMS 自身） | 实：ls 行数=`____` / 裸名存在？`[ ]否/[ ]是=FAIL`；SHA256SUMS 条目数=`____`（应 5） | `[ ]` |
| 4.1.2 | **sha256sum -c 硬断言**（在上面 TMP 内执行）：<br>`cd "$TMP" && sha256sum -c SHA256SUMS 2>&1 \| tee /tmp/sha256_result.log && echo "--- summary ---" && grep -cE ": OK$" /tmp/sha256_result.log` | 结果必须 `5/5 OK`（或 asset_count-1 / asset_count）；严禁 4/5；严禁 `FAILED` 行；summary `: OK` count 必须 = SHA256SUMS 条目数 | 实：OK count=`____ / ____`；FAILED 行=`____` | `[ ]` |

### 4.2 O9 线上即时清理（1 项 · 若 O5 三保险生效可自动跳过）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 4.2.1 | **若 §3.1.3 asset_count ≠ 6 或出现裸名 `agentlisp` / `agentlisp.exe` → 立刻执行 O9 线上清理**（否则本项跳过打勾即可）：<br>`VERSION=v_______; for ASSET in agentlisp agentlisp.exe; do gh release delete-asset "$VERSION" "$ASSET" -R 4TWS3/agentLisp -y 2>&1 \| true; done`，然后在 §4.1.1 的 TMP 内重算 SHA：`cd "$TMP" && rm -f SHA256SUMS agentlisp agentlisp.exe && ls \| xargs sha256sum > SHA256SUMS && gh release upload --clobber "$VERSION" SHA256SUMS -R 4TWS3/agentLisp`；最后 §3.1.3 重新查 asset_count 必须 6 | 最终 `gh release view --json assets \| jq '.assets | length'` = 6；sha256sum -c 仍 5/5 OK | 本项是否需要执行：`[ ]否，asset_count已6 直接打勾 / [ ]是，执行后 asset_count=`____ | `[ ]` |

### 4.3 3 平台 CLI smoke 验证（2 项 · 至少本地 1 平台跑）

| # | 命令 VERBATIM | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 4.3.1 | **本地方案 smoke（`agentlisp --version` 匹配 tag）**：从 §4.1.1 的 TMP 取对应你平台的 CLI：<br>macOS arm64：`cd "$TMP" && chmod +x agentlisp-macos-arm64 && ./agentlisp-macos-arm64 --version`<br>Linux x86_64：`./agentlisp-linux-x86_64 --version`<br>Windows x86_64（需 wine/Windows 机器）：`agentlisp-windows-x86_64.exe --version` | stdout 必须含 `agentlisp, version X.Y.Z` 与 `$VERSION` 语义一致；exit=0；严禁 segmentation fault / DLL 缺失 | 实：平台=`________`；version 输出=`________________`；exit=`____` | `[ ]` |
| 4.3.2 | **本地方案 help smoke（非空 + 3 大子命令）**：同上，取对应平台 CLI：<br>`./agentlisp-* --help 2>&1 \| grep -E "^  (check|run|compile|emit)" \| wc -l`（子命令名以实际为准，至少 2+） | `wc -l` ≥ 2；help 非空；exit=0 | 实：子命令数=`____`；help 输出空？`[ ]否` | `[ ]` |

---

## §5. External & Handoff（发布后收尾 · 共 N 项 = 外部依赖核查 + 制度化 Handoff）

> 本节不是阻塞项（除 5.1 外），但影响项目可维护性，必须在发布后 24h 内完成全部。

### 5.1 外部 τ²-bench 真源三向全等（1 项 · 每次 Release 必须重跑确保外部仓库未被意外篡改）

| # | 命令 VERBATIM | 预期值（字节级全等 CR-36 C1-4 基准） | 本次实填 | 通过？ |
|---|---|---|---|---|
| 5.1.1 | **τ²-bench 三件套指纹重验**：<br>`T2TMP=$(mktemp -d) && gh release download τ²-bench-v1.0 -R 4TWS3/t2-bench -D "$T2TMP" --clobber`<br>(a) sha256：`cd "$T2TMP" && sha256sum -c SHA256SUMS 2>&1 \| grep -c ": OK$"`（=2）<br>(b) fingerprint 逐行 + 累计：<br>`python3 -c "<br>import hashlib, json<br>AGG = hashlib.sha256()<br>lines = open('$T2TMP/samples.jsonl').read().strip().split('\n')<br>assert len(lines)==1000, f'lines={len(lines)}'<br>mis = 0<br>for line in lines:<br>    row = json.loads(line)<br>    fp_decl = row['fingerprint_sha256']<br>    row_no_fp = dict(row); del row_no_fp['fingerprint_sha256']<br>    fp_calc = hashlib.sha256(json.dumps(row_no_fp, sort_keys=True, ensure_ascii=False).encode()).hexdigest()<br>    AGG.update((fp_calc+'\\n').encode())<br>    if fp_decl != fp_calc: mis += 1<br>print('mismatch:', mis)<br>print('AGG:', AGG.hexdigest())<br>print('AGG == DECL:', AGG.hexdigest() == open('$T2TMP/README.md').read().split('FINGERPRINT_AGG_SHA256 = ')[1].split()[0].strip())<br>"` | (a) 2/2 OK；<br>(b) mismatch=0；AGG= `d9306d6a70e3fb03e78c0741199af4481a22dfd2644c5e4a888d4c2600a22f7b`（字节全等）；AGG==DECL=True | 实：(a)=`____/2 OK`；(b) mismatch=`____`；AGG=`________________________________` / 全等声明？`[ ]` | `[ ]` |

### 5.2 SRS 文档回写（2 项 · 制度化 Roadmap 对齐）

| # | 任务要点（非阻塞，人工编辑 SRS） | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 5.2.1 | **SRS §附录 C C-3 行**：追加本次 Release 的 RUN ID / head_sha / asset_count / Docker digest 4 条信息（参照 C-3 行 v2.0.0-rc2 终态描述格式） | 原文中 C-3 描述末尾追加本次新 Release 元信息；保留历史 Release 信息（不覆盖，便于审计） | 完成：`[ ]` | `[ ]` |
| 5.2.2 | **SRS §附录 D O 类优化池**：若本次 Release 触发了任何新 O 类（如 O12 PyPI publish 新流程等），先写 `in_progress（CR-XX）`，完成后写 `✅ Completed（CR-XX）` | 无新增 O 类 → 直接打勾；有 → 至少 in_progress 行存在 | O 类新增数：`____` | `[ ]` |

### 5.3 制度化 Handoff 产出（1 项 · 不交付即失格）

| # | 命令 VERBATIM / 要点 | 预期值（7 章标题 grep 全等） | 本次实填 | 通过？ |
|---|---|---|---|---|
| 5.3.1 | **新建 Handoff 文档到 `docs/handoff/YYYYMMDD_crXX_crYY_${ACTION}_handoff.md`**，7 章严格：<br>`## 1. Git 状态核验` / `## 2. 四硬指标验证快照` / `## 3. 每项交付的具体改动 + 精确代码锚` / `## 4. 未跑/可选验证项（U1-Ux）` / `## 5. 硬约束 + 34-ID VERBATIM + 外部端点` / `## 6. 顺位路线图（下一条顺位）` / `## 7. 交接人签字 + 四硬终态锚`<br>核查：`grep -nE "^## [1-7]\\." docs/handoff/$(ls -t docs/handoff | head -1) \| wc -l` = 7 | 7 章齐全；标题字节全等（不允许自定义 `## 0.` 或 `## 8.`）；文件大小 ≥ 20KB | 实：新文件=`________________________`；7 章 grep 数=`____`（=7 通过）；size=`____KB` | `[ ]` |

### 5.4 PyPI Publish 制度化必过小节（O12 · 7 步 · 非可选，除非明确跳）

> **制度化触发**：自 v2.0.0-rc3 起，所有正式 Release（含 rc）必须执行 PyPI Publish；若因 TestPyPI 试点阶段需跳，须明确登记原因。

#### 5.4.0 PyPI 前置配置（**首次发布前一次性完成，后续 Release 只需登记状态**）

| # | 核查要点 · 命令/人工 | 预期值 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 5.4.0-1 | **1 包发布策略确认**：仅发布根 `agentlisp==$VERSION`（三合一 runtime+host+python/agentlisp_runtime），子 `agentlisp-runtime` 不发 PyPI（保持 file:// 直引本地） | 一致 = 1 包 | 本次策略：`[ ]1 包 / [ ]2 包` | `[ ]` |
| 5.4.0-2 | **Trusted Publisher 配置（零 token 方案 · 账号级录入，非项目级）**：<br>(a) **登录 PyPI 后直接访问：`https://pypi.org/manage/account/publishing/`**（PyPI 新版界面已移除项目级「Add project」按钮——恶意抢注防护；现在必须先上传包才创建项目，Pending Publisher 在 **账号级** 预先配置，首次发布时自动创建项目并激活）<br>(b) 点击「Add a new pending publisher」→ 表单 4 字段字节级严格全等：Owner=`4TWS3`；Repository name=`agentLisp`；Workflow name=`release.yml`；Environment name=`pypi`<br>（TestPyPI 同样操作：**同样账号级** `https://test.pypi.org/manage/account/publishing/` → 相同 4 字段，仅 **Environment name=`testpypi`** 不同；项目名 PyPI / TestPyPI 都统一为 `agentlisp`，无需 TestPyPI 另起不同名）<br>⚠️ **抢注风险提示（制度化必须知悉）**：Pending Publisher **不会**帮您保留项目名；若在首次发布前有人上传同名 `agentlisp` 包，该配置会失效，项目名被占用，必须立即换名或联系 PyPI admins。**建议在本步骤完成后 ≤ 24 小时内推进 B 线 RC-4 首次发布。** | (a)+(b) Pending Publisher 列表可查 2 条记录（pypi + testpypi）；首次 GitHub Actions 发布 OIDC 校验通过后 → 状态从 pending → active → 项目自动创建 | PyPI 账号级 pypi 条目：`[ ]待发布 / [ ]已发布(active)`；账号级 testpypi 条目：`[ ]待发布 / [ ]已发布(active)`；配置时间：`YYYY-MM-DD` | `[ ]` |
| 5.4.0-3 | **根 pyproject.toml PyPI 元数据齐全核查**：<br>人工读根 pyproject.toml `[project]` + `[project.urls]`：存在 authors/maintainers/keywords(≥8)/classifiers(≥10) + Homepage/Repository/"Bug Tracker"/Documentation/"Release Notes"/SRS 共 6 URLs | 元数据齐全 | 本次核查：`keywords=`____个/`classifiers=`____个/`urls=`____个 | `[ ]` |
| 5.4.0-4 | **release.yml publish-pypi job 存在性核查**：<br>`grep -c "^  publish-pypi:" .github/workflows/release.yml` 必须 =1；environment.name=pypi；pypa/gh-action-pypi-publish@release/v1 uses | 存在 1 个 publish-pypi job；uses 正确 | `grep count=`____；uses 正确？`[ ]` | `[ ]` |
| 5.4.0-5 | **GitHub Environment: pypi 创建**：<br>Settings → Environments → New → `Name: pypi` → Environment protection rules 勾选 Required reviewers（至少 1 名 4TWS3 成员）+ Wait timer=0；Deployment branches: Selected → Add: `refs/tags/v*` | Environment pypi 存在；Required reviewers ≥1 | 创建日期：`________`；Reviewers（至少 1 人）：`________` | `[ ]` |

#### 5.4.1 本次 Release PyPI 发布流程（7 步 · 制度化）

| # | 步骤 · 命令 VERBATIM / 人工核查要点 | 预期值 / PASS 条件 | 本次实填 | 通过？ |
|---|---|---|---|---|
| 5.4.1-1 | **TestPyPI 试点（仅首次/rc 版必跑；GA 可跳但推荐）**：<br>临时修改 release.yml publish-pypi job 两行：environment.name=`testpypi` + with.repository-url=`https://test.pypi.org/legacy/` → 打 rc tag 触发 CI → 然后 gh release 下载 whl + sdist →：<br>`VERSION=v_____; PKG=${VERSION#v}; python3 -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ --dry-run agentlisp==$PKG 2>&1 | TestPyPI 上 `agentlisp==$PKG` 可见；--dry-run 不报错（实际安装推荐用 venv：`pip install --index-url https://test.pypi.org/simple/ agentlisp[dev]==$PKG && agentlisp --version && python3 -c "import runtime, host, agentlisp_runtime; print('OK')"`） | TestPyPI 安装 dry-run 通过？`[ ]`；实装 import 成功？`[ ]` | `[ ]` |
| 5.4.1-2 | **release.yml publish-pypi job 状态轮询**（§3 结束后再开始，避免并发）：<br>`RUN_ID=________; gh run view "$RUN_ID" -R 4TWS3/agentLisp --json jobs 2>&1 \| python3 -c "import json,sys; d=json.load(sys.stdin); [print(j['name'], '→', j['status']+'/'+j.get('conclusion','-')) for j in d['jobs'] if 'pypi' in j['name'].lower()]"` | `Publish to PyPI (Trusted Publisher OIDC) → completed/success`；OIDC 登录阶段无 403（表明 Trusted Publisher 生效） | Job 名称=`________`；conclusion=`________`；OIDC 无 403？`[ ]` | `[ ]` |
| 5.4.1-3 | **SHA256 全等（PyPI ↔ GitHub Release ↔ 本地 §4.1）**：<br>三份文件必须 `sha256sum` 64 hex 字节级全等：<br>① GH release 下载的 `agentlisp-$PKG-py3-none-any.whl`；② PyPI 发布后 PyPI 提供的 sha256（或从 publish-pypi job `print-hash: true` 输出取）；③ 本地 §4.1.1 TMP 下同名文件<br>取三者 sha256 对照：<br>`GH_SHA=$(gh release view $VERSION -R 4TWS3/agentLisp --json assets 2>&1 \| python3 -c "import json,sys; [print(a['name'], a['size']) for a in json.load(sys.stdin)['assets']]"; sha256sum "agentlisp-$PKG-py3-none-any.whl"` | ①=②=③ 三 sha256 完全相同（64 hex 全等） | whl: ①=②？`[ ]`；②=③？`[ ]`；sdist: ①=②=③？`[ ]` | `[ ]` |
| 5.4.1-4 | **PyPI 正式 3 步 smoke（必须本地 venv 实装，禁止 --dry-run 跳过）**：<br>`TMPENV=$(mktemp -d); python3 -m venv "$TMPENV" && source "$TMPENV/bin/activate" && python3 -m pip install --upgrade pip 2>&1 \| tail -1`<br>(a) `pip install agentlisp==$PKG 2>&1 \| tail -3` 无 ERROR<br>(b) `agentlisp --version 2>&1` 输出含 "agentlisp, version $PKG"<br>(c) `python3 -c "import runtime; import host; import agentlisp_runtime; from runtime.base_harness import BaseHarness; from runtime.checker import Checker; from host.gateway import create_app; print('All 3 modules + 3 key imports OK')"` | (a) exit=0 无 ERROR；(b) version 精确匹配；(c) stdout 末行 `All 3 modules + 3 key imports OK` | (a) 实际最后 3 行：`________________`；(b) version：`________`；(c) 3 关键 import：`[ ]` | `[ ]` |
| 5.4.1-5 | **PyPI 项目页元数据核查**：<br>浏览器或 `curl -s https://pypi.org/pypi/agentlisp/$PKG/json \| python3 -c "import json,sys; d=json.load(sys.stdin)['info']; print('classifiers=', len(d.get('classifiers',[]))); print('keywords=', len(d.get('keywords') or [])); print('urls=', list(d.get('project_urls',{}).keys()))"` | classifiers≥10；keywords≥8；urls 至少 5 项（Homepage/Repository/Bug Tracker/Documentation/Release Notes/SRS） | classifiers=`____`；keywords=`____`；urls 6 项齐全？`[ ]` | `[ ]` |
| 5.4.1-6 | **Legacy extras 可用性验证（非阻塞但推荐）**：<br>同一 venv：`pip install "agentlisp[llm,mcp,web,durable,observability,sandbox,dev]==$PKG" 2>&1 \| tail -3`；然后 `python3 -c "import anthropic, openai, fastapi, temporalio, redis, opentelemetry, docker; print('All 7 extras install OK')"` | 无安装 ERROR；7 个 extras import 全通过 | 安装 exit=0？`[ ]`；7 关键 import：`[ ]` / 跳过说明：`________` | `[ ]` |
| 5.4.1-7 | **首次 TestPyPI 成功 → 切回正式 PyPI**：若 §5.4.1-1 临时改 environment/repository-url，发布完成后必须 **立即 revert release.yml 为 pypi 正式**（不提交 TestPyPI 定制版本到主线） | release.yml publish-pypi environment.name=pypi；repository-url 未硬编码（默认 PyPI） | git diff release.yml 含 TestPyPI 改动？`[ ]否 / [ ]是 → revert 了？[ ]` | `[ ]` |

#### 5.4.2 失败回滚（PyPI 版号永不复用红线）

| 情形 | 回滚动作 VERBATIM | 本次是否触发 |
|---|---|---|
| 5.4.2-1 | publish-pypi job 失败（OIDC 403 / build 失败 / 元数据 fail） | **不删 tag**；只修 release.yml 或 pyproject.toml 元数据；推新 commit + 新 `rcX` tag 递增重试（禁止覆写旧 tag） | `[ ]未触发 / [ ]触发→新tag=________` |
| 5.4.2-2 | PyPI 成功但 5.4.1-3/5.4.1-4 失败（**PyPI 上已存在该版号 = 永不复用红线**） | **禁止 `twine upload --skip-existing` 同版号**；必须递增 patch/prerel tag（如 rc2→rc3）发新版 PyPI；旧版号保留在 PyPI（不 yank 除非严重） | `[ ]未触发 / [ ]触发→新tag=________；是否 yank 旧版？[ ]否/[ ]是(原因:________)` |

---

### 5.5 其他可选外部发布（N 项 · 非阻塞，按需勾选）

| # | 选项 · 触发前置 + 命令要点 | 是否执行 | 本次实填 |
|---|---|---|---|
| 5.5.1 | **Homebrew Tap（若有 4TWS3/homebrew-tap 仓库）**：更新 `Formula/agentlisp.rb` 的 url + sha256（macOS arm64/x86_64 bottle sha256） | `[ ]否 / [ ]是` | Tap commit：`________` |
| 5.5.2 | **Release Note 美化（gh release edit）**：<br>`VERSION=v_______; gh release edit "$VERSION" -R 4TWS3/agentLisp --notes-file docs/RELEASE_NOTES_${VERSION//./_}.md`（若需独立 notes 文件） | `[ ]否 / [ ]是` | Notes 文件 size：`____KB` |
| 5.5.3 | **社群公告（Discussion / 微信群 / README Badge 更新）**：README.md 首屏 6 徽章中的 Release / pytest / SRS / τ²-bench 数值是否已对齐新版本号 | `[ ]否 / [ ]是 → README commit: ________` | 徽章对齐：`[ ]` |

---

## §末 · 本次 Release Checklist 总览（自动汇总勾选项）

| 节 | 应完成项数 | 实际完成 `[x]` 数 | 通过率 | 阻塞？ |
|---|---|---|---|---|
| §0 元信息 | 5 字段全填 | ____ / 5 | ____% | `[ ]否 / [ ]是=禁止打签` |
| §1 Pre-Flight | 11 | ____ / 11 | ____% | `[ ]否 / [ ]是=禁止打签` |
| §2 Tag & Push | 5 | ____ / 5 | ____% | `[ ]否 / [ ]是=禁止进入§3` |
| §3 CI Build Watch | 6 | ____ / 6 | ____% | `[ ]否 / [ ]是=禁止进入§4` |
| §4 Post Release | 5 | ____ / 5 | ____% | `[ ]否 / [ ]是=禁止宣告GA` |
| §5 External & Handoff | 5.1 必过 + 5.2/5.3 必做 + 5.4 可选 | 必过 ____ / 3 | ____% | `[ ]否 / [ ]是=24h内补齐` |
| **总计（必过）** | **32（不含5.4可选）** | **____ / 32** | **____%** | **[ ] ALL GREEN 宣告成功 🎉 / [ ] 有 FAIL，立刻回滚排查** |

> **失败回滚路径（VERBATIM，若 §2~§4 任何一步 FAIL）**：
> 1. 若 tag 已 push 但 CI FAIL → `git push origin :refs/tags/$VERSION`（删远程 tag）+ `gh release delete $VERSION -R 4TWS3/agentLisp -y`（删远程 Release draft）+ `git tag -d $VERSION`（删本地 tag）
> 2. 回到 §1 重查四硬/C1 9禁动 → 修复代码或调整配置 → 从 §0 重新填写新 Checklist → 重新走全流程
> 3. **严禁在 FAIL 的 Release tag 上 amend / force push**；一律删 tag + 重打新 tag（版本号后缀递增，如 rc2→rc3）
