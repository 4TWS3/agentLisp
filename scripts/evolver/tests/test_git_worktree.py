"""US-50 / FR-EVO-5：Worktree 验证后清理。"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.evolver.worktree import GitWorktree, git_env


def _init_repo(path: Path) -> Path:
    env = git_env()
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, env=env)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=a@b",
            "-c",
            "user.name=a",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=path,
        check=True,
        env=env,
    )
    return path


def test_worktree_created_then_removed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo")
    wt = GitWorktree(repo, name="t1")
    with wt as d:
        assert d.is_dir()
        assert (d / ".git").exists()
        assert (d / ".git").read_text(encoding="utf-8").find("gitdir:") >= 0
    assert not wt.dir.exists(), "退出后必须清理 worktree"


def test_worktree_cleaned_on_exception(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path / "repo2")
    wt = GitWorktree(repo, name="t2")
    with pytest.raises(RuntimeError), wt:
        raise RuntimeError("boom")
    assert not wt.dir.exists(), "异常路径也必须清理"
