"""AgentLisp τ²-bench 数据集加载与本地合成 resolver。

对齐 SRS §6.3 AC-3：每条样本 (sample_id, buggy_code, baseline_a_report, required_tools, optional_patch_hints)
经由 harness.react → 生成修复 → 评估三条件 AND → detail 行。

本模块只负责「加载/解析样本」，不负责执行与评估（执行在 runtime/base_harness_v2.py / 评估在 run_t2_bench.py T2BenchEvaluator）。

三种 Resolver（按优先级从上到下尝试，不依赖某一种）：
 1) LocalDirectoryResolver(path) — 本地已解包的 t2-bench@v1.0 release assets 目录
    结构：
      samples/t2-v1_00001.jsonl
        或 samples.jsonl [{"sample_id": "t2-v1_00001", ...}]
 2) GitHubReleaseResolver(gh_cli_path=None) — 调用 `gh release download τ²-bench-v1.0`
    下载到 --cache-dir（默认 $HOME/.cache/agentlisp/t2-bench-v1.0）
 3) DryRunResolver(n, seed) — 离线合成样本，保证 CI 无外网也能稳定产出 1000 条
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("AgentLisp.T2Bench.Fetch")

T2_V1_REPO = "4TWS3/t2-bench"
T2_V1_TAG = "τ²-bench-v1.0"
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "agentlisp" / "t2-bench-v1.0"


@dataclasses.dataclass(frozen=True)
class T2Sample:
    """一条 t2-bench v1.0 样本。字段对齐 GitHub Release asset schema。"""

    sample_id: str
    baseline_a_pass: bool
    buggy_code: str
    language: str
    original_failed_tests: list[str]
    required_tools: list[str]
    rubric_hints: list[str]
    patch_hints: list[str]
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def fingerprint_sha256(self) -> str:
        payload = "||".join(
            [
                self.sample_id,
                self.language,
                self.buggy_code,
                ",".join(sorted(set(self.original_failed_tests))),
                ",".join(sorted(set(self.required_tools))),
            ]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FetchError(RuntimeError):
    """resolver 加载失败时抛出。"""


# ==========================================================
# Resolver #1：本地解包目录
# ==========================================================
class LocalDirectoryResolver:
    def __init__(self, base_dir: str | os.PathLike[str]) -> None:
        self.base = Path(base_dir).expanduser().resolve()

    def available(self) -> bool:
        return self.base.is_dir()

    def load(self, sample_range: tuple[int, int] | None) -> list[T2Sample]:
        if not self.available():
            raise FetchError(f"Local dir not exists: {self.base}")
        samples_jsonl = self.base / "samples.jsonl"
        files = sorted(
            [
                *(self.base.glob("*.jsonl")),
                *(self.base.glob("samples/*.jsonl")),
                *(self.base.glob("**/samples.jsonl")),
            ]
        )
        rows: list[dict[str, Any]] = []
        if samples_jsonl.is_file():
            rows.extend(_load_jsonl(samples_jsonl))
        for fp in files:
            if fp == samples_jsonl:
                continue
            rows.extend(_load_jsonl(fp))
        if not rows:
            raise FetchError(f"No samples.jsonl / *.jsonl found under {self.base}")
        samples = [_row_to_sample(r) for r in rows]
        samples.sort(key=lambda s: s.sample_id)
        samples = _apply_range(samples, sample_range)
        logger.info("LocalDirectoryResolver loaded %d samples from %s", len(samples), self.base)
        return samples


# ==========================================================
# Resolver #2：调用 gh 从 GitHub Release 下载到本地 cache 再用 Local 加载
# ==========================================================
class GitHubReleaseResolver:
    def __init__(
        self,
        repo: str = T2_V1_REPO,
        tag: str = T2_V1_TAG,
        cache_dir: str | os.PathLike[str] = DEFAULT_CACHE_DIR,
        gh_cli: str | None = None,
    ) -> None:
        self.repo = repo
        self.tag = tag
        self.cache_dir = Path(cache_dir).expanduser().resolve()
        self.gh_cli = gh_cli or shutil.which("gh") or "gh"

    def available(self) -> bool:
        return shutil.which(self.gh_cli.split()[0]) is not None

    def load(self, sample_range: tuple[int, int] | None) -> list[T2Sample]:
        if not self.available():
            raise FetchError(f"`{self.gh_cli}` not in PATH，无法拉 t2-bench release")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        lockfile = self.cache_dir / ".fetched.ok"
        if not lockfile.is_file():
            logger.info("Downloading %s@%s → %s", self.repo, self.tag, self.cache_dir)
            cmd = [
                *self.gh_cli.split(),
                "release",
                "download",
                self.tag,
                "-R",
                self.repo,
                "-D",
                str(self.cache_dir),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                raise FetchError(
                    f"`gh release download` failed. stderr={exc.stderr[-400:]}"
                ) from exc
            lockfile.write_text("ok\n", encoding="utf-8")
        return LocalDirectoryResolver(self.cache_dir).load(sample_range)


# ==========================================================
# Resolver #3：离线合成样本（和 generate_dry_run_samples 的分布保持一致）
# ==========================================================
class DryRunResolver:
    def __init__(
        self,
        n: int,
        seed: int,
        *,
        target_fix_rate: float = 0.92,
        target_baseline_rate: float = 0.75,
    ) -> None:
        self.n = max(1, int(n))
        self.seed = int(seed)
        self.target_fix_rate = target_fix_rate
        self.target_baseline_rate = target_baseline_rate

    def available(self) -> bool:
        return True

    def fallback_message(self) -> str:
        """AC-3 真实数据集不可用时的 DryRunResolver 降级提示（pytest skip + run_t2_bench.py 可直接展示）。

        三段式：① 不可用原因（本地缺 cache + 缺 gh CLI）；② 一键拉取命令；③ 合成样本保证行为（t2-v1_{00001..N} sample_id 固定，seed 确定）。
        """
        fetch_cmd = f"gh release download {T2_V1_TAG!r} -R {T2_V1_REPO!r} -D {DEFAULT_CACHE_DIR}"
        return (
            "[AC-3 τ²-bench DRY-RUN FALLBACK] "
            "True dataset not available (no local cache at "
            f"{DEFAULT_CACHE_DIR} and no `gh` CLI in PATH). "
            f"Fetch with: {fetch_cmd}. "
            f"Using deterministic DryRunResolver(n={self.n}, seed={self.seed}) "
            f"with sample_id range t2-v1_00001..t2-v1_{self.n:05d} "
            f"(target_fix_rate={self.target_fix_rate:.2f}, target_baseline_rate={self.target_baseline_rate:.2f})."
        )

    def load(self, sample_range: tuple[int, int] | None) -> list[T2Sample]:
        rng = random.Random(self.seed)
        samples: list[T2Sample] = []
        for i in range(1, self.n + 1):
            baseline_pass = rng.random() < self.target_baseline_rate
            b_pass_prob = self.target_fix_rate + (0.10 if not baseline_pass else -0.05)
            b_pass = rng.random() < max(0.0, min(1.0, b_pass_prob))
            # 合成 buggy 代码与失败用例，便于 harness 真执行
            buggy_lines, failed_tests = _synthesize_buggy_python(i, rng, b_pass, baseline_pass)
            samples.append(
                T2Sample(
                    sample_id=f"t2-v1_{i:05d}",
                    baseline_a_pass=baseline_pass,
                    buggy_code="\n".join(buggy_lines) + "\n",
                    language="python",
                    original_failed_tests=failed_tests,
                    required_tools=["bash"],
                    rubric_hints=[
                        "修复后 pytest 不得有 deselect/skip/xfail",
                        "reviewer-agent 综合 rubric 分 ≥0.8",
                    ],
                    patch_hints=[],
                    metadata={
                        # 保存合成真值，便于离线验证 evaluator 三条件 AND 的正确性
                        "__dry_run__": True,
                        "__expected_t2_pass__": b_pass,
                        "__expected_cond1_compile_pass__": b_pass or rng.random() < 0.98,
                        "__expected_cond2_pytest_pass__": b_pass or rng.random() < 0.96,
                        "__expected_rubric_score__": round(
                            min(
                                1.0,
                                max(
                                    0.0,
                                    (
                                        rng.uniform(0.80, 0.99)
                                        if b_pass
                                        else rng.uniform(0.55, 0.7999)
                                    ),
                                ),
                            ),
                            4,
                        ),
                    },
                )
            )
        samples = _apply_range(samples, sample_range)
        logger.info(
            "DryRunResolver synthesized %d samples seed=%d baseline_rate=%.2f target_fix_rate=%.2f",
            len(samples),
            self.seed,
            self.target_baseline_rate,
            self.target_fix_rate,
        )
        return samples


# ==========================================================
# 内部 helpers
# ==========================================================
def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("%s line %d invalid JSONL line: %s (skipping)", path, line_no, exc)
    return rows


def _row_to_sample(row: dict[str, Any]) -> T2Sample:
    sid = str(
        row.get("sample_id") or row.get("id") or f"t2-unk_{abs(hash(str(row))) % 1_000_000:06d}"
    )
    original_failed = row.get("original_failed_tests") or row.get("failing_tests") or []
    required = row.get("required_tools") or row.get("tools") or ["bash"]
    rubric = row.get("rubric_hints") or row.get("rubric") or []
    patch = row.get("patch_hints") or row.get("hints") or []
    return T2Sample(
        sample_id=sid,
        baseline_a_pass=bool(row.get("baseline_a_pass", False)),
        buggy_code=str(row.get("buggy_code") or row.get("code") or ""),
        language=str(row.get("language") or "python").lower(),
        original_failed_tests=[str(x) for x in list(original_failed)],
        required_tools=[str(x) for x in list(required)],
        rubric_hints=[str(x) for x in list(rubric)],
        patch_hints=[str(x) for x in list(patch)],
        metadata={
            k: v
            for k, v in row.items()
            if k
            not in {
                "sample_id",
                "id",
                "baseline_a_pass",
                "buggy_code",
                "code",
                "language",
                "original_failed_tests",
                "failing_tests",
                "required_tools",
                "tools",
                "rubric_hints",
                "rubric",
                "patch_hints",
                "hints",
            }
        },
    )


def _apply_range(samples: list[T2Sample], sample_range: tuple[int, int] | None) -> list[T2Sample]:
    if sample_range is None:
        return samples
    start, end = sample_range
    start = max(1, int(start))
    end = min(len(samples), int(end))
    if start > end:
        return []
    return samples[(start - 1) : end]


def _synthesize_buggy_python(
    i: int, rng: random.Random, new_b_pass: bool, baseline_pass: bool
) -> tuple[list[str], list[str]]:
    """合成一段简短的可 pytest 化的 Python buggy 代码 + 失败用例名。

    为了让 evaluator 离线跑时能稳定映射真值：
    - __expected_t2_pass__=True  → 给出无错代码（三条件都 True）
    - __expected_t2_pass__=False → 随机让其中一个条件显式失败（更贴近真实分布）
    """
    func_name = f"adder_{i:05d}"
    bug_kind = 0 if new_b_pass else rng.choice([1, 2, 3])
    # code:
    lines = [
        f"# sample t2-v1_{i:05d} synthesized buggy python",
        "",
    ]
    if bug_kind == 1:
        # 语法错误（cond1 compile_pass=False → 立即 0.01 runtime_error_rate 命中）
        lines.append(f"def {func_name}(a, b)")
        lines.append("    return a + b")
    elif bug_kind == 2:
        # 语义错误但能编译（cond1 True；pytest 必然失败 → cond2 False）
        lines.append(f"def {func_name}(a, b):")
        lines.append("    return a - b  # BUG: minus instead of plus")
    elif bug_kind == 3:
        # 代码正确但风格/可读性差（rubric 预期低）
        lines.append(f"def {func_name}(a,b):")
        lines.append(f"    # TODO(john): x+y={func_name}")
        lines.append("    s=a+b")
        lines.append(f"    return (s + (0 * {i}) )")
    else:
        # 修复后：干净代码三条件都 True
        lines.append(f"def {func_name}(a: int, b: int) -> int:")
        lines.append('    """Return a + b."""')
        lines.append("    return a + b")

    failed = []
    if bug_kind in {2, 3} or baseline_pass is False:
        failed = [f"test_addition_{i:05d}"]
    return lines, failed
