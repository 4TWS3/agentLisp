"""产物漂移（drift）闸门端到端测试。

被测对象：`compiler/main.rkt` 的产物指纹机制 + `file-content-drifted?` 判定。
来源：AMS `core/release.py` 的 MANIFEST/detect_drift 思路（见 ADR 式讨论），
      agentLisp 侧改为**产物内嵌全文件 sha256** —— 不额外生成清单文件。

为什么必须端到端跑（不能只测纯函数）：
  本机制的价值全在「重编译时到底写不写盘」这一个行为上。
  只测 `sha256-hex` / `digest-of-unsigned` 会漏掉三处真实缺陷，
  这三处本轮都实际踩到（见各测试的 docstring）。

判据（机器拦，非人记）：
  1. 同源两次编译 → 产物**逐字节相同**（确定性，否则 drift 判定无意义）；
  2. 内嵌指纹 == Python hashlib 独立复算值（两个独立实现互证）；
  3. 生成后手工改动 → 重编译拒绝写盘（exit 3）且文件不变；
  4. `--force` 覆盖；
  5. `--check-output-drift` 只读报告（clean=0 / drifted=1）。
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
SOURCE = ROOT / "examples" / "repair_agent.al"

# racket 可能不在 PATH（minimal 发行版常放仓库内 .racket/bin）
_BUNDLED_RACKET = ROOT / ".racket" / "bin" / "racket"
RACKET = (
    "racket"
    if shutil.which("racket")
    else (str(_BUNDLED_RACKET) if _BUNDLED_RACKET.exists() else None)
)
HAS_RACKET = RACKET is not None

FINGERPRINT_FIELD = "_AGENTLISP_CONTENT_SHA256"
# 宽口径：占位形态（空值）与已签名形态（64 位 hex）都要能被规范化。
# 为什么不是 {64}：指纹要对「字段留空的文本」自洽计算，写死 64 位就匹配不上占位形态。
SIGNED_RE = re.compile(rf'{FINGERPRINT_FIELD}\s*=\s*"([0-9a-f]{{64}})"')
ANY_RE = re.compile(rf'{FINGERPRINT_FIELD}\s*=\s*"[0-9a-f]{{0,64}}"')


def _canonical(text: str) -> str:
    """把指纹字段置空 —— 与 Racket 侧 canonical-for-sha256 同一口径。"""
    return ANY_RE.sub(f'{FINGERPRINT_FIELD} = ""', text)


def _compile(out: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    assert RACKET is not None
    return subprocess.run(
        [RACKET, "compiler/main.rkt", "-i", str(SOURCE), "-o", str(out), *extra],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


pytestmark = pytest.mark.skipif(
    not HAS_RACKET, reason="racket 不可用（PATH 与 .racket/bin 均未找到）"
)


@pytest.mark.req("IF-CLI-1")
def test_compile_embeds_fingerprint_matching_python_hashlib(tmp_path: Path) -> None:
    """判据 2：产物内嵌指纹必须等于 Python hashlib 独立复算值。

    这是**跨实现互证**：Racket 侧是自写 SHA-256（标准库无 sha256），
    若只由它自己声明「我算对了」，那就是自我证明。
    """
    out = tmp_path / "agent.py"
    proc = _compile(out)
    assert proc.returncode == 0, proc.stderr[-800:]

    src = out.read_text(encoding="utf-8")
    m = SIGNED_RE.search(src)
    assert m, "产物缺少已签名指纹字段"
    expected = hashlib.sha256(_canonical(src).encode("utf-8")).hexdigest()
    assert m.group(1) == expected, "Racket 指纹与 Python hashlib 复算值不一致"


@pytest.mark.req("IF-CLI-1")
def test_recompile_is_byte_identical(tmp_path: Path) -> None:
    """判据 1：同源两次编译产物逐字节相同。

    反证价值：若指纹把「时间戳/绝对路径」拌进去，第二次编译就不相等，
    drift 判定会永远报漂移 —— 这条测试拦住那种实现。
    """
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    assert _compile(first).returncode == 0
    assert _compile(second).returncode == 0
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.req("IF-CLI-1")
def test_check_output_drift_reports_clean_then_drifted(tmp_path: Path) -> None:
    """判据 5：只读校验的两种报告（CLEAN=0 / DRIFTED=1），且不改文件。

    反证价值：本轮实现初版只把**生成段**纳入指纹，产物尾注不在覆盖范围，
    于是在产物末尾追加一行后仍报 CLEAN（假绿）。此测试即拦该缺陷。
    """
    out = tmp_path / "agent.py"
    assert _compile(out).returncode == 0
    generated = out.read_bytes()

    clean = _compile(out, "--check-output-drift")
    assert clean.returncode == 0, clean.stdout
    assert "CLEAN" in clean.stdout
    # 只读：校验不得改动文件
    assert out.read_bytes() == generated

    # 在**末尾**追加（尾注位于指纹覆盖范围之外时最容易漏检）
    with out.open("a", encoding="utf-8") as fh:
        fh.write("\n# 手工追加\n")

    drifted = _compile(out, "--check-output-drift")
    assert drifted.returncode == 1, drifted.stdout
    assert "DRIFTED" in drifted.stdout


@pytest.mark.req("IF-CLI-1")
def test_guard_refuses_to_overwrite_hand_edited_artifact(tmp_path: Path) -> None:
    """判据 3：生成后被手工改动 → 重编译拒绝写盘、exit 3、文件保持原样。"""
    out = tmp_path / "agent.py"
    assert _compile(out).returncode == 0
    with out.open("a", encoding="utf-8") as fh:
        fh.write("\n# 手工追加\n")
    edited = out.read_bytes()

    proc = _compile(out)
    assert proc.returncode == 3, f"期望 exit 3（IO 失败档），实际 {proc.returncode}"
    assert "refusing to overwrite" in proc.stderr
    assert "--force" in proc.stderr, "拒绝时未告知出口（--force）"
    assert out.read_bytes() == edited, "拒绝后文件仍被改写"


@pytest.mark.req("IF-CLI-1")
def test_force_overwrites_hand_edited_artifact(tmp_path: Path) -> None:
    """判据 4：--force 覆盖手工改动（显式放弃保护）。"""
    out = tmp_path / "agent.py"
    assert _compile(out).returncode == 0
    with out.open("a", encoding="utf-8") as fh:
        fh.write("\n# 手工追加\n")

    proc = _compile(out, "--force")
    assert proc.returncode == 0, proc.stderr[-800:]
    assert "手工追加" not in out.read_text(encoding="utf-8")


@pytest.mark.req("IF-CLI-1")
def test_unmarked_file_is_overwritten_without_force(tmp_path: Path) -> None:
    """无指纹文件（旧产物 / 手写文件）不算漂移 —— 保持向后兼容，可自由写。

    为什么这样定：0.x 时代产物与手写文件都没有指纹。若把它们一律判为漂移，
    升级本功能后第一次重编译就会全线拒绝写盘。
    """
    out = tmp_path / "legacy.py"
    out.write_text("# 老产物，没有指纹\n", encoding="utf-8")

    proc = _compile(out)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert SIGNED_RE.search(out.read_text(encoding="utf-8")), "重编译后仍未写入指纹"
