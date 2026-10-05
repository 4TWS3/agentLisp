"""CR-21 P2-5 τ²-bench dataset 存在性 + DryRunResolver fallback 降级消息 pytest。

绑定 SRS：
  - AC-3 §6.3（真实数据集 1000 样本 fix_rate ≥ 0.90）
  - 代码锚：scripts/bench/fetch_t2_dataset.py（LocalDirectoryResolver / DryRunResolver）
  - SSOT：AC-3 数据集下载命令：
      gh release download τ²-bench-v1.0 -R agentlisp/t2-bench -D $HOME/.cache/agentlisp/t2-bench-v1.0
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_BENCH = REPO_ROOT / "scripts" / "bench"
for _p in (str(REPO_ROOT), str(SCRIPTS_BENCH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fetch_t2_dataset import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    T2_V1_REPO,
    T2_V1_TAG,
    DryRunResolver,
    LocalDirectoryResolver,
    T2Sample,
)


def test_t2_bench_dataset_presence_or_skip_with_dry_run_fallback_message() -> None:
    """P2-5 AC-3 数据集存在性双路径：
    A) 真实数据集存在（$HOME/.cache/agentlisp/t2-bench-v1.0 含 samples.jsonl）：
       - 加载条数 == 1000
       - 1000 条 sample_id 唯一（无重复）
       - sample_id 前缀全为 "t2-v1_"
       - 每条 T2Sample fingerprint_sha256 长度 == 64 字符
    B) 真实数据集不存在（缺 gh CLI 或没 fetch）：
       - pytest.skip(fallback_message)，fallback_message 三段式包含：
         "[AC-3 τ²-bench DRY-RUN FALLBACK]" + gh 下载命令 + DryRunResolver(n,seed) 确定性行为说明
    """
    local = LocalDirectoryResolver(DEFAULT_CACHE_DIR)
    if local.available():
        samples = local.load(sample_range=None)
        assert len(samples) == 1000, (
            f"LocalDirectoryResolver loaded {len(samples)} samples，AC-3 基线应为 1000"
        )
        ids = [s.sample_id for s in samples]
        assert len(set(ids)) == 1000, "1000 条 sample_id 唯一（无重复 AC-3 违反）"
        for s in samples:
            assert isinstance(s, T2Sample)
            assert s.sample_id.startswith("t2-v1_"), f"sample_id 前缀异常：{s.sample_id!r}"
            assert len(s.fingerprint_sha256()) == 64, "fingerprint_sha256 非 64 字符 hex"
        return
    dry = DryRunResolver(n=1000, seed=42)
    msg = dry.fallback_message()
    assert "[AC-3 τ²-bench DRY-RUN FALLBACK]" in msg
    assert T2_V1_TAG in msg
    assert T2_V1_REPO in msg
    assert str(DEFAULT_CACHE_DIR) in msg
    assert "gh release download" in msg
    assert "DryRunResolver(n=1000, seed=42)" in msg
    pytest.skip(msg)


def test_dry_run_resolver_100_samples_sample_ids_unique_and_prefix_ok() -> None:
    """P2-5 DryRunResolver(n=100, seed=123) 确定性行为验证：
    - 100 条 sample_id 唯一
    - 前缀 t2-v1_ 正确
    - baseline_a_pass ∈ {True, False}
    - fingerprint_sha256 == 64 hex chars
    （离线不依赖真实数据集或 gh CLI，永远可跑，保证严格模式 +1 passed）
    """
    dry = DryRunResolver(n=100, seed=123)
    samples = dry.load(None)
    assert len(samples) == 100
    ids = [s.sample_id for s in samples]
    assert len(set(ids)) == 100, "DryRunResolver 100 条 sample_id 必须唯一"
    for s in samples:
        assert s.sample_id.startswith("t2-v1_")
        assert s.baseline_a_pass in {True, False}
        fp = s.fingerprint_sha256()
        assert len(fp) == 64
        int(fp, 16)  # hex parseable，否则抛 ValueError
