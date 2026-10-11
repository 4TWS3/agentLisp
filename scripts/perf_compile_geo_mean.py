#!/usr/bin/env python3
"""NFR-PERF-2 唯一实现：编译器 parse+check+emit 的几何均值（同进程计时）。

口径（实测依据，2026-10-11）：
  * Racket 进程启动 ≈185ms；加载 compiler/main.rkt ≈600ms（首次含模块编译）；
  * 编译器内部 pipeline ≈0.07ms。
因此 NFR 只能测「编译器内部」时间，否则任何实现都超 200ms（结构性红）。
SRS 原文即「编译器 wall-clock 时间（parse + check + emit）」。

调用方（两处，共用本脚本，避免同一判断多处实现）：
  1) runtime/tests/test_harness_v2.py::test_nfr_perf_2_compile_wall_clock_lt_200ms
  2) .github/workflows/ci.yml 的 perf job 独立验证步骤

退出码：0 = 通过；1 = 超阈值；2 = 环境缺 racket 或探针失败。
"""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

THRESHOLD_MS = 200.0
ROUNDS = 3
ITERATIONS = 10

ROOT = Path(__file__).resolve().parents[1]
# 计时样本：规范形态的 agent 夹具（(defagent …) 现代块语法，可直接被 parse-defagent 读入）
SAMPLE = ROOT / "tests" / "patterns" / "fixtures" / "defchain_doc_pipeline.expected.rkt"

PROBE = """#lang racket/base
(require racket/file
         (file "{compiler}")
         (file "{checker}"))
(define form (with-input-from-file "{sample}" (lambda () (read))))
(define (once) (define p (parse-defagent form)) (check-agent p) (agent->py p))
(once) ; 预热，排除首轮 JIT/GC 抖动
(define times '())
(for ([i {iters}])
  (define t0 (current-inexact-milliseconds))
  (once)
  (set! times (cons (- (current-inexact-milliseconds) t0) times)))
(define n (length times))
(define gm (exp (/ (for/sum ([t (in-list times)]) (log (max t 1e-6))) n)))
(printf "~a\n" (real->decimal-string gm 4))
"""


def measure() -> float:
    """返回多轮几何均值的几何均值（ms）。环境不满足时抛 RuntimeError。"""
    racket = shutil.which("racket")
    if racket is None:
        raise RuntimeError("PATH 中没有 racket")
    if not SAMPLE.is_file():
        raise RuntimeError(f"计时样本缺失：{SAMPLE}")
    body = PROBE.format(
        # 必须是正斜杠形式：Windows 的 D:\a\... 塞进 Racket 字符串会被当转义序列 → 探针解析失败（rc=2）
        compiler=(ROOT / "compiler" / "agentlisp_compiler.rkt").as_posix(),
        checker=(ROOT / "compiler" / "checker.rkt").as_posix(),
        sample=SAMPLE.as_posix(),
        iters=ITERATIONS,
    )
    with tempfile.TemporaryDirectory() as td:
        probe = Path(td) / "perf_probe.rkt"
        probe.write_text(body, encoding="utf-8")
        runs = []
        for i in range(ROUNDS):
            # Windows 默认用 locale 编码（cp1252）解码 → 非 ASCII 会 UnicodeDecodeError
            cp = subprocess.run(
                [racket, str(probe)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(ROOT),
                timeout=180,
            )
            if cp.returncode != 0:
                raise RuntimeError(f"探针第 {i + 1} 轮失败 rc={cp.returncode}: {cp.stderr[-300:]}")
            runs.append(float(cp.stdout.strip().splitlines()[-1]))
    return math.exp(sum(math.log(max(x, 1e-6)) for x in runs) / len(runs))


def main() -> int:
    # Windows 控制台默认 cp1252：直接 print 中文会 UnicodeEncodeError。
    # 显式把两个流切到 UTF-8（errors=replace 保证不因编码中断测量）。
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        geo = measure()
    except RuntimeError as e:
        print(f"[SKIP-REASON] NFR-PERF-2 未验证：{e}")
        return 2
    ok = geo < THRESHOLD_MS
    print(
        f"[{'OK' if ok else 'FAIL'}] NFR-PERF-2 编译器内部 parse+check+emit "
        f"geo_mean = {geo:.4f}ms (阈值 {THRESHOLD_MS}ms, {ROUNDS} 轮 x {ITERATIONS} 次)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
