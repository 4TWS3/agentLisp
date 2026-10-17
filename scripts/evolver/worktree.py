"""隔离 Git Worktree（FR-EVO-5 / US-50）：进入创建，退出必清理。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def git_env() -> dict[str, str]:
    """清掉继承来的 GIT_* 变量。

    为什么：从 git hook 里跑时，git 会设 GIT_DIR / GIT_INDEX_FILE。
    不清掉，子 git 命令会操作**错误的仓库**（实测：提交门禁里 worktree 测试必红）。
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


class GitWorktree:
    def __init__(self, repo: str | Path, base_ref: str = "HEAD", name: str = "evolver") -> None:
        self.repo = Path(repo).resolve()
        self.base_ref = base_ref
        self.dir = self.repo.parent / (self.repo.name + "-evolver-worktree-" + name)

    def __enter__(self) -> Path:
        if self.dir.exists():
            shutil.rmtree(self.dir, ignore_errors=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "worktree",
                "add",
                "--detach",
                str(self.dir),
                self.base_ref,
            ],
            check=True,
            capture_output=True,
            text=True,
            env=git_env(),
        )
        return self.dir

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.dir.exists():
            subprocess.run(
                ["git", "-C", str(self.repo), "worktree", "remove", "--force", str(self.dir)],
                check=False,
                capture_output=True,
                text=True,
                env=git_env(),
            )
        shutil.rmtree(self.dir, ignore_errors=True)
        prune = subprocess.run(
            ["git", "-C", str(self.repo), "worktree", "prune"],
            check=False,
            capture_output=True,
            text=True,
            env=git_env(),
        )
        _ = prune
