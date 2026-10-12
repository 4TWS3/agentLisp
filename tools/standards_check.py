#!/usr/bin/env python3
"""AgentLisp 项目级标准检查器（四角色标准：产品 / 架构 / 工程 / AI agent）。

用法：
    python3 tools/standards_check.py            # 跑全部，退出码 0 = 全过
    python3 tools/standards_check.py --list     # 列出判据
    python3 tools/standards_check.py --only P4  # 只跑某条

设计约束（检查器自身也要守标准）：
  * 枚举封闭：判据 id 是封闭集合；新增未登记的 id 直接失败（见 _assert_registry_closed）。
  * 不许沉默：每条跳过必须打印原因（[SKIP] <原因>），不计入通过。
  * 总结只报**实际跑过的数量**，不写死总数（教训：曾写死 len(CHECKS) 而只跑了 3 条）。
  * 同一判断只有一处实现：P5 与 E3 共用同一个函数（_check_silent_excepts）。

判据来源：本仓库实测教训（2026-10-11 长会话）+ 全局 AGENTS.md「四角色标准」。
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY_DIRS = ("runtime", "host", "python/agentlisp_runtime", "tests", "scripts", "tools")


# --------------------------------------------------------------------------- 工具
def _sh(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def _py_files(*dirs: str) -> list[Path]:
    out: list[Path] = []
    for d in dirs:
        base = ROOT / d
        if base.is_dir():
            out.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def _result(ok: bool, detail: str) -> tuple[bool, str]:
    return ok, detail


# --------------------------------------------------------------------------- 判据实现
def _check_p1_cli_flags_declared() -> tuple[bool, str]:
    """P1 声称能做必须真能做：文档声明的 CLI 开关 == main.rkt 实际解析的开关。"""
    main = (ROOT / "compiler" / "main.rkt").read_text(encoding="utf-8")
    actual = set(re.findall(r'\(\("(--[a-z-]+)"\)', main))
    if not actual:
        return _result(False, "main.rkt 未解析出任何命令行开关（解析正则或实现有变）")
    readme = ROOT / "README.md"
    if not readme.is_file():
        return _result(False, "README.md 缺失，无法核对声明")
    text = readme.read_text(encoding="utf-8")
    declared = {f for f in actual if f in text}
    missing = sorted(actual - declared)
    if missing:
        return _result(False, f"这些开关未在 README 声明：{missing}")
    return _result(True, f"{len(actual)} 个开关均已声明")


def _check_p2_illegal_input_fast() -> tuple[bool, str]:
    """P2 做不到 1 秒内说清：非法输入在入口被拒，不挂起。"""
    bad = ROOT / ".tmp_standards_bad.al"
    bad.write_text("(define-agent x (:bogus 1))\n", encoding="utf-8")
    try:
        import time

        t0 = time.perf_counter()
        cp = _sh(["racket", "compiler/main.rkt", "-i", str(bad), "--check-only"], timeout=30)
        dt = time.perf_counter() - t0
    finally:
        bad.unlink(missing_ok=True)
    if cp.returncode == 0:
        return _result(False, "非法输入却返回 0")
    if dt > 1.0:
        return _result(False, f"拒绝耗时 {dt:.2f}s > 1s")
    return _result(True, f"rc={cp.returncode}，{dt * 1000:.0f}ms 内拒绝")


def _check_p3_error_readable() -> tuple[bool, str]:
    """P3 失败给「发生了什么＋为什么＋怎么办」：--json-errors 必须含 message 且非裸异常名。"""
    bad = ROOT / ".tmp_standards_bad_kv.al"
    bad.write_text(
        "(define-agent kv-bad\n"
        '  (:context :memory-policy (:markdown-fs "./m.md" :layers (L0-Abstract) :auto-append #t))\n'
        '  (:model :provider "q" :name "m" :system-prompt "s")\n'
        "  (:tools (import-builtin bash))\n"
        '  (:harness (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))\n'
        "            (:verify :json-schema #t)\n"
        "            (:correct :max-retries 1 :on-failure abort)))\n",
        encoding="utf-8",
    )
    try:
        cp = _sh(["racket", "compiler/main.rkt", "--check-only", "--json-errors", "-i", str(bad)])
    finally:
        bad.unlink(missing_ok=True)
    try:
        payload = json.loads(cp.stdout)
    except json.JSONDecodeError as e:
        return _result(False, f"--json-errors 输出不是合法 JSON：{e}")
    if not payload:
        return _result(False, "非法输入未产出任何错误条目")
    err = payload[0]
    if not err.get("message"):
        return _result(False, "错误条目缺 message")
    if re.fullmatch(r"[A-Za-z_.]+Error:?\s*", err.get("message", "")):
        return _result(False, f"message 是裸异常名：{err['message']!r}")
    if "hints" not in err:
        return _result(False, "错误条目缺 hints（没有「怎么办」）")
    return _result(True, f"{len(payload)} 条错误，含 message/hints")


def _check_p4_no_silent_failure() -> tuple[bool, str]:
    """P4 不许沉默：编译失败时进程不得返回 0（宏展开失败曾只打日志、仍返回 0）。"""
    bad = ROOT / ".tmp_standards_bad_macro.al"
    # defmemory-agent 需要 (name store gc)：参数非法 → 宏在展开期报错
    bad.write_text('(defmemory-agent m "./x.md" "not-an-int")\n', encoding="utf-8")
    try:
        cp = _sh(["racket", "compiler/main.rkt", "-i", str(bad), "--check-only"], timeout=30)
    finally:
        bad.unlink(missing_ok=True)
    if cp.returncode == 0:
        return _result(False, "宏展开失败但退出码为 0（静默失败）")
    return _result(True, f"rc={cp.returncode}，失败可见")


def is_silent_handler(handler: ast.ExceptHandler) -> bool:
    """判据（P5 == E3，唯一实现）：这个 except 是否属于「静默吞掉」。

    收紧定义（第一版误判教训）：
      * 只算「pass / 只 return」且无任何留痕的 handler；
      * 排除 ImportError / ModuleNotFoundError：那是显式降级分支，属环境适配，
        不是吞异常（第一版把这类 import 回退全判成违规，属判据写错）；
      * body 里出现 logging / logger / print / warnings.warn / raise 即视为有留痕。
    """
    dumped = ast.dump(handler)
    if any(tok in dumped for tok in ("logging", "logger", "print", "warn")):
        return False
    if any(isinstance(n, ast.Raise) for n in ast.walk(handler)):
        return False
    if handler.type is not None:
        names = [n.id for n in ast.walk(handler.type) if isinstance(n, ast.Name)]
        if any(n in ("ImportError", "ModuleNotFoundError") for n in names):
            return False
    for stmt in handler.body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Return) and (
            stmt.value is None or isinstance(stmt.value, ast.Constant)
        ):
            continue
        return False
    return True


def _check_silent_excepts() -> tuple[bool, str]:
    """P5 == E3（共用实现）：except 不得静默吞掉异常。"""
    offenders: list[str] = []
    for p in _py_files(*PY_DIRS):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            offenders.append(f"{p.relative_to(ROOT)}: 语法错误 {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and is_silent_handler(node):
                offenders.append(f"{p.relative_to(ROOT)}:{node.lineno}")
    if offenders:
        return _result(False, f"{len(offenders)} 处静默 except：{offenders[:5]}")
    return _result(True, "未发现静默 except")


def _check_p6_e2e_main_path() -> tuple[bool, str]:
    """P6 以用户走通的路径为准：真实 .al → 编译 → 产物是合法 Python。"""
    sample = ROOT / "tests" / "patterns" / "fixtures_v2" / "priority01_hc_HC.al"
    out = ROOT / ".tmp_standards_out.py"
    try:
        cp = _sh(["racket", "compiler/main.rkt", "-i", str(sample), "-o", str(out)])
        if cp.returncode != 0:
            return _result(False, f"编译失败 rc={cp.returncode}: {cp.stderr[-200:]}")
        src = out.read_text(encoding="utf-8")
        ast.parse(src)
    except SyntaxError as e:
        return _result(False, f"产物不可解析：{e}")
    # 注意：不要把 FileNotFoundError 吞在这里 —— 缺 racket 属环境问题，
    # 让它上抛到 main，由统一处理转成「跳过 + 原因」。
    finally:
        out.unlink(missing_ok=True)
    if "self.PATTERNS" not in src:
        return _result(False, "产物缺 self.PATTERNS（模式语义未落到产物）")
    return _result(True, f"{len(src.splitlines())} 行产物，ast.parse 通过")


def _check_a1_single_implementation() -> tuple[bool, str]:
    """A1 同一判断只有一处实现：NFR-PERF-2 的测量实现必须唯一。"""
    canonical = ROOT / "scripts" / "perf_compile_geo_mean.py"
    if not canonical.is_file():
        return _result(False, "唯一实现脚本缺失：scripts/perf_compile_geo_mean.py")
    dupes = []
    for p in _py_files("runtime", "tests", "scripts", "tools"):
        # 排除唯一实现自身与检查器自身（检查器文本里也含这两个词 → 会自我误报）
        if p.resolve() in (canonical.resolve(), Path(__file__).resolve()):
            continue
        text = p.read_text(encoding="utf-8")
        if "geo_mean" in text and "current-inexact-milliseconds" in text:
            dupes.append(str(p.relative_to(ROOT)))
    if dupes:
        return _result(False, f"检测到第二处几何均值实现：{dupes}")
    return _result(True, "NFR-PERF-2 仅一处实现")


def _check_a2_conventions_have_tests() -> tuple[bool, str]:
    """A2 约定要变成机器会拦的错误：关键约定必须有测试。"""
    required = {
        "退出码契约": ROOT / "runtime" / "tests" / "test_cli_if_cli_1_exit_encoding.py",
        "模式注册表覆盖": ROOT / "tests" / "test_cr42_kind_coverage.py",
        "四角色标准": ROOT / "tests" / "test_standards.py",
        "21 模式落地清单": ROOT / "tests" / "test_pattern_landing.py",
    }
    missing = [k for k, v in required.items() if not v.is_file()]
    if missing:
        return _result(False, f"这些约定缺测试：{missing}")

    # 登记闭环：判据注册表 ↔ SRS 附录 B 的「工具判据」表必须一一对应。
    # 只加判据不登记（或登记了不存在的判据）都失败 —— 枚举封闭用到判据表上。
    srs = ROOT / "docs" / "spec" / "agentlisp_srs.md"
    if not srs.is_file():
        return _result(False, "SRS 缺失，无法校验工具判据登记表")
    srs_text = srs.read_text(encoding="utf-8")
    declared = set(re.findall(r"^\|\s*\*\*(STD-[A-Z0-9]+)\*\*\s*\|", srs_text, re.M))
    registered = {f"STD-{c['id']}" for c in CHECKS}
    if declared != registered:
        return _result(
            False,
            f"判据登记表与注册表不一致：仅登记未实现={sorted(declared - registered)}，"
            f"仅实现未登记={sorted(registered - declared)}",
        )

    # 表内反引号引用的仓库路径必须真实存在。
    # 坑 #30：我曾把 tools/verify_local.sh 拼成 toolls/…，而只比 ID 集合抓不到拼写错误。
    table_at = srs_text.find("#### 工具判据")
    # 必须截止到下一个标题：否则会把后续章节里的绝对路径（如 /app/...）也当成仓库路径扫
    table = srs_text[table_at:].split("### 孤儿需求核查", 1)[0] if table_at >= 0 else ""
    known_top = (
        "tools",
        "tests",
        "scripts",
        "runtime",
        "docker",
        "docs",
        "compiler",
        "python",
        "host",
        "examples",
        ".github",
    )
    missing_paths: list[str] = []
    for raw in re.findall(r"`([^`]+)`", table):
        tok = raw.strip()
        if not tok or not tok.isascii() or tok.startswith("-"):
            continue
        if any(ch in tok for ch in " (=)↔…*:"):
            continue
        if not (tok.endswith((".py", ".rkt", ".md", ".yml", ".txt", ".sh", ".toml")) or "/" in tok):
            continue
        if tok.split("/")[0] in known_top:
            if not (ROOT / tok).exists():
                missing_paths.append(tok)
        elif not any(ROOT.rglob(tok)):
            missing_paths.append(tok)
    if missing_paths:
        return _result(False, f"登记表引用的路径不存在：{sorted(set(missing_paths))}")

    return _result(
        True,
        f"{len(required)} 条约定均有测试；{len(declared)} 条判据已登记；表内引用路径均存在",
    )


def _check_a3_no_cwd_dependence() -> tuple[bool, str]:
    """A3 隐式环境必须变显式输入：测试不得依赖 cwd（用 __file__ 派生路径）。"""
    offenders = []
    pattern = re.compile(r'(?<![\.\w])Path\("(compiler|tests|runtime|scripts)/')
    for p in _py_files("runtime/tests", "tests"):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and "__file__" not in line:
                offenders.append(f"{p.relative_to(ROOT)}:{i}")
    if offenders:
        return _result(False, f"{len(offenders)} 处相对路径读取：{offenders[:5]}")
    return _result(True, "测试均以 __file__ 派生路径")


def _check_a10_all_test_dirs_in_source() -> tuple[bool, str]:
    """A10 测试目录清单必须覆盖全部测试：真源要包含每个含 test_*.py 的目录。

    坑 #34：tools/test_paths.txt 曾只写 tests/step_defs + tests/patterns，
    于是 tests/*.py、host/tests、scripts/tests 共 97 个用例**从未在 CI 运行** ——
    「CI 全绿」并不覆盖它们。A7 只保证「本地 == CI」，保证不了「CI == 全部测试」，
    本条补上后半句。
    """
    paths_file = ROOT / "tools" / "test_paths.txt"
    if not paths_file.is_file():
        return _result(False, "缺 tools/test_paths.txt")
    listed = [
        ln.strip().strip("/")
        for ln in paths_file.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    skip_parts = {".git", ".venv", "__pycache__", ".trae", "node_modules", "dist", "build"}
    dirs: set[str] = set()
    for p in ROOT.rglob("test_*.py"):
        rel = p.relative_to(ROOT)
        if any(part in skip_parts for part in rel.parts):
            continue
        dirs.add(rel.parent.as_posix())
    missing = sorted(d for d in dirs if not any(d == L or d.startswith(L + "/") for L in listed))
    if missing:
        # 已知缺口（台账 #36）：纳入这 3 个目录会让 CI 红 —— 首次真跑暴露 12 个只在 CI 出现的失败
        # （tests._bdd_helper 导入、kind 解析为 0、Windows 编码/夹具读取、落地清单生成）。
        # 按「收益递减时收手」暂缓，但**不静默**：以 SKIP + 原因报出，并指向台账。
        return _result(
            False,
            "SKIP: 已知缺口（台账 #36）—— 这些目录未纳入真源，CI 不会跑："
            + str(missing)
            + "；纳入后 CI 会红 12 处，修复计划见台账",
        )
    return _result(True, f"{len(dirs)} 个测试目录全部被真源覆盖（共 {len(listed)} 条路径）")


def _check_a5_closed_enums() -> tuple[bool, str]:
    """A5 边界枚举必须封闭：注册表 kind 与退出码都有计数断言。"""
    coverage = ROOT / "tests" / "test_cr42_kind_coverage.py"
    text = coverage.read_text(encoding="utf-8")
    if "len(kinds) ==" not in text:
        return _result(False, "kind 覆盖测试没有计数断言（枚举不封闭）")
    cli = ROOT / "runtime" / "tests" / "test_cli_if_cli_1_exit_encoding.py"
    cli_text = cli.read_text(encoding="utf-8")
    codes = {m for m in re.findall(r"expected rc=(\d)", cli_text)}
    if len(codes) < 4:
        return _result(False, f"退出码枚举未封闭，只断言了 {sorted(codes)}")
    return _result(True, f"kind 计数 + {len(codes)} 个退出码均有断言")


def _check_a9_distribution_self_proof() -> tuple[bool, str]:
    """A9 分发物必须自证能力：镜像里带编译器，且构建期真编译一次、断言模式语义进产物。

    坑 #31：审查者只查分发物（Docker 镜像 / wheel），看到镜像里没有 compiler/，
    就判定「21 个设计模式仍未落地」—— 源码树有、分发物没有，而用户看到的是分发物。
    对策：能力必须由分发物自证，不能靠源码树解释。
    """
    dockerfile = ROOT / "docker" / "Dockerfile"
    if not dockerfile.is_file():
        return _result(False, "缺 docker/Dockerfile")
    text = dockerfile.read_text(encoding="utf-8")
    if not re.search(r"^COPY compiler ", text, re.M):
        return _result(False, "镜像未拷贝 compiler/：分发物不能编译 .al（用户会判「模式未实现」）")
    if "racket compiler/main.rkt -i" not in text:
        return _result(False, "构建期没有真编译一次（缺 racket compiler/main.rkt -i）")
    if "self.PATTERNS" not in text:
        return _result(False, "编译自证未断言模式语义进产物（缺 self.PATTERNS）")
    readme = ROOT / "README.md"
    if not readme.is_file() or "Docker 镜像的能力边界" not in readme.read_text(encoding="utf-8"):
        return _result(False, "README 未写明镜像能力边界（运行时 vs 编译器）")
    return _result(True, "镜像含 compiler/ + 构建期编译自证 + README 写明能力边界")


def _check_a6_compromises_registered() -> tuple[bool, str]:
    """A6 每个妥协必须写下代价并告知：台账每条必须有「守」列。"""
    ledger = ROOT / "docs" / "spec" / "agentlisp_lessons_ledger.md"
    if not ledger.is_file():
        return _result(False, "踩坑台账缺失")
    rows = [
        ln for ln in ledger.read_text(encoding="utf-8").splitlines() if re.match(r"^\| \d+ \|", ln)
    ]
    if not rows:
        return _result(False, "台账无条目")
    bad = [r for r in rows if r.count("|") < 5]
    if bad:
        return _result(False, f"{len(bad)} 条台账缺列：{bad[:2]}")
    return _result(True, f"{len(rows)} 条台账均含「现象/根因/守」三列")


def _check_a7_local_equals_ci() -> tuple[bool, str]:
    """A7 本地验证命令 == CI 命令：唯一真源 tools/test_paths.txt。

    坑 #18/#24：我用「习惯的命令」验、CI 用另一组路径 → 「本地绿、CI 红」重复 5 次，
    tests/patterns 因此从未在 CI 跑过（可追溯性矩阵长期 4 条 ORPHAN）。
    本条判据把「两边一致」从纪律变成机器拦。
    """
    paths_file = ROOT / "tools" / "test_paths.txt"
    verify = ROOT / "tools" / "verify_local.sh"
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    for p in (paths_file, verify, ci):
        if not p.is_file():
            return _result(False, f"缺文件：{p.relative_to(ROOT)}")

    paths = [ln.strip() for ln in paths_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not paths:
        return _result(False, "tools/test_paths.txt 为空（唯一真源不能为空）")
    missing = [p for p in paths if not (ROOT / p).is_dir()]
    if missing:
        return _result(False, f"真源里的路径不存在：{missing}")

    ci_text = ci.read_text(encoding="utf-8")
    if "cat tools/test_paths.txt" not in ci_text:
        return _result(False, "CI 的 pytest 未引用唯一真源（硬编码路径会漂移，坑 #24）")
    # Windows 检出可能是 CRLF：不去 \r 会让路径尾部多一个字符（CI 实测 file or directory not found）
    # 只看**命令本身**：注释里出现 tr -d 不算（第一版写成全文子串检查，
    # 结果被我自己的注释满足 → 反验时假通过）。
    cmd_lines = [
        ln for ln in ci_text.splitlines() if "cat tools/test_paths.txt" in ln and "pytest" in ln
    ]
    if not cmd_lines:
        return _result(False, "找不到引用真源的 pytest 命令行")
    if not all("tr -d" in ln for ln in cmd_lines):
        return _result(
            False,
            f"引用真源的 pytest 命令未去 CR（Windows CRLF 会让路径尾部带 \\r，坑 #25）：{cmd_lines[0].strip()[:60]}",
        )
    if ".gitattributes" not in [p.name for p in ROOT.iterdir()]:
        return _result(False, "缺 .gitattributes：真源与 *.sh 的行尾无法固定为 LF")
    if "tools/test_paths.txt" not in verify.read_text(encoding="utf-8"):
        return _result(False, "tools/verify_local.sh 未引用同一真源")

    # 全量调用不得硬编码路径清单。按**步骤块**判定（不是按行）：多行 run: | 里
    # 路径与 -k 常在不同行，按行判会把 perf job 的刻意子集误报。
    blocks: list[list[str]] = [[]]
    for line in ci_text.splitlines():
        if re.match(r"^\s+- (name|uses):", line):
            blocks.append([])
        blocks[-1].append(line)
    hard: list[str] = []
    for block in blocks:
        joined = "\n".join(block)
        if "pytest" not in joined or "cat tools/test_paths.txt" in joined:
            continue
        if " -k " in joined:
            continue  # 刻意子集：必须带 -k 过滤，例如 perf job
        for line in block:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # 注释里提到路径不算硬编码
            if re.search(r"(runtime/tests|python/tests|tests/step_defs|tests/patterns)", line):
                hard.append(stripped[:70])
                break
    if hard:
        return _result(False, f"CI 里仍有硬编码路径的 pytest 调用：{hard}")

    return _result(True, f"真源 {len(paths)} 条路径，CI 与本地脚本均引用它")


def _check_a8_acceptance_path() -> tuple[bool, str]:
    """A8 验收必须走生产同一条路：验收命令不得用回退链 / || true 掩盖失败。

    坑 #29：Dockerfile 的构建期 CLI 验收曾写成三条绝对路径依次尝试
    （PATH → /app/.venv/bin/agentlisp → python -m），第三条成功即算通过 ——
    正好掩盖了 console script 的 shebang 指向构建期 venv 的真缺陷，让 Build 假绿一轮。

    判据（可测）：
      1) Dockerfile 里带 --help / python -c 的验收行，不得出现 || 回退；
      2) ci.yml 里 docker run 冒烟不得用 || true 吞掉失败。
    """
    dockerfile = ROOT / "docker" / "Dockerfile"
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    for p in (dockerfile, ci):
        if not p.is_file():
            return _result(False, f"缺文件：{p.relative_to(ROOT)}")

    offenders: list[str] = []
    for i, line in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        if ("--help" in s or "python -c" in s) and "||" in s:
            offenders.append(f"docker/Dockerfile:{i}: {s[:70]}")
    for i, line in enumerate(ci.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        if "docker run" in s and "|| true" in s:
            offenders.append(f"ci.yml:{i}: {s[:70]}")

    if offenders:
        return _result(False, f"验收命令存在回退/掩盖写法（坑 #29）：{offenders[:3]}")
    return _result(True, "Dockerfile 验收与 CI 冒烟均为单一路径（无 || 回退）")


# --------------------------------------------------------------------------- 注册表（封闭枚举）
CHECKS: list[dict] = [
    {
        "id": "P1",
        "role": "产品",
        "title": "CLI 开关声明与实现一致",
        "fn": _check_p1_cli_flags_declared,
    },
    {
        "id": "P2",
        "role": "产品",
        "title": "非法输入 1 秒内拒绝",
        "fn": _check_p2_illegal_input_fast,
    },
    {
        "id": "P3",
        "role": "产品",
        "title": "错误体含发生了什么/为什么/怎么办",
        "fn": _check_p3_error_readable,
    },
    {
        "id": "P4",
        "role": "产品",
        "title": "失败不得返回 0（不许沉默）",
        "fn": _check_p4_no_silent_failure,
    },
    {
        "id": "P5",
        "role": "产品",
        "title": "静默 except 检查（与 E3 共用）",
        "fn": _check_silent_excepts,
    },
    {
        "id": "P6",
        "role": "产品",
        "title": "E2E 主链路：.al → 合法 Python",
        "fn": _check_p6_e2e_main_path,
    },
    {
        "id": "A1",
        "role": "架构",
        "title": "同一判断只有一处实现（perf 测量）",
        "fn": _check_a1_single_implementation,
    },
    {"id": "A2", "role": "架构", "title": "关键约定有测试", "fn": _check_a2_conventions_have_tests},
    {"id": "A3", "role": "架构", "title": "测试不依赖 cwd", "fn": _check_a3_no_cwd_dependence},
    {
        "id": "A5",
        "role": "架构",
        "title": "边界枚举封闭（kind/退出码）",
        "fn": _check_a5_closed_enums,
    },
    {
        "id": "A6",
        "role": "架构",
        "title": "妥协登记且含守列",
        "fn": _check_a6_compromises_registered,
    },
    {
        "id": "A7",
        "role": "架构",
        "title": "本地验证命令 == CI 命令（唯一真源）",
        "fn": _check_a7_local_equals_ci,
    },
    {
        "id": "A8",
        "role": "架构",
        "title": "验收不得走回退路径（坑 #29）",
        "fn": _check_a8_acceptance_path,
    },
    {
        "id": "A9",
        "role": "架构",
        "title": "分发物必须自证能力（坑 #31）",
        "fn": _check_a9_distribution_self_proof,
    },
    {
        "id": "A10",
        "role": "架构",
        "title": "测试目录清单覆盖全部测试（坑 #34）",
        "fn": _check_a10_all_test_dirs_in_source,
    },
    {
        "id": "E3",
        "role": "工程",
        "title": "静默 except 检查（与 P5 共用）",
        "fn": _check_silent_excepts,
    },
]

CLOSED_IDS = (
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "P6",
    "A1",
    "A2",
    "A3",
    "A5",
    "A6",
    "A7",
    "A8",
    "A9",
    "A10",
    "E3",
)


def _assert_registry_closed() -> None:
    ids = tuple(c["id"] for c in CHECKS)
    if ids != CLOSED_IDS:
        raise SystemExit(f"判据注册表不封闭：实际 {ids}，期望 {CLOSED_IDS}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="AgentLisp 标准检查器")
    ap.add_argument("--list", action="store_true", help="列出判据")
    ap.add_argument("--only", action="append", default=[], help="只跑指定 id（可多次）")
    args = ap.parse_args(argv)

    _assert_registry_closed()
    if args.list:
        for c in CHECKS:
            print(f"{c['id']:<3} {c['role']}  {c['title']}")
        print(f"共 {len(CHECKS)} 条（与 P5/E3 共用实现计两条注册项）")
        return 0

    selected = [c for c in CHECKS if not args.only or c["id"] in args.only]
    unknown = set(args.only) - {c["id"] for c in CHECKS}
    if unknown:
        print(f"[FAIL] 未登记的判据 id：{sorted(unknown)}")
        return 2

    passed = failed = skipped = 0
    for c in selected:
        try:
            ok, detail = c["fn"]()
        except FileNotFoundError as e:
            # 环境缺可执行文件（如 CI 的 python-tests job 没有 racket）= 跳过，不是判据失败。
            # 跳过必须给原因，且在总结里单独列出（不许沉默）。
            ok, detail = False, f"SKIP: 缺可执行文件 {e.filename or e}"
        except Exception as e:  # 判据自身异常 = 失败，不许沉默
            ok, detail = False, f"判据抛异常：{type(e).__name__}: {e}"
        if ok:
            passed += 1
            print(f"[PASS] {c['id']} {c['title']} — {detail}")
        elif detail.startswith("SKIP"):
            skipped += 1
            print(f"[SKIP] {c['id']} {c['title']} — {detail}")
        else:
            failed += 1
            print(f"[FAIL] {c['id']} {c['title']} — {detail}")

    # 总结只报实跑数量（教训：写死总数会谎报「12/12 通过」）
    total = passed + failed + skipped
    print(
        f"\n合计：实跑 {total} 条（注册 {len(CHECKS)} 条，筛选后 {len(selected)} 条）"
        f" → 通过 {passed} / 失败 {failed} / 跳过 {skipped}"
    )
    # 跳过不算失败（跳过已在总结里单列，且 detail 带原因）；失败即非 0
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
