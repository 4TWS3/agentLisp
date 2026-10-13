"""生产适配器（设计 v2 §7）：把 Mock 换成真实实现。

- FileSkillStore：learning 的技能层落盘（真实文件系统 ✓ 契约 CT-LEARNING-01 的「落盘 + 下次生效」）
- FileCorpusRetriever：rag/topic-model 的本地语料检索（真实读盘 ✓ 无语料时返回空并告警）

硬规则：真实适配器**不打** adapter=mock 告警；Mock 一律告警（见 ports.py）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileSkillStore:
    """技能层落盘：key → <dir>/<sanitized key>.json。"""

    adapter = "file"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        return self.root / f"{safe}.json"

    def put(self, key: str, value: Any) -> None:
        self._path(key).write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get(self, key: str) -> Any:
        p = self._path(key)
        if not p.is_file():
            return None
        return json.loads(p.read_text(encoding="utf-8"))


class FileCorpusRetriever:
    """本地语料检索：读 <dir>/**/*.txt|md，按子串命中。"""

    adapter = "file"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.calls: list[tuple[str, int]] = []

    def _docs(self) -> list[tuple[str, str]]:
        if not self.root.is_dir():
            logger.warning("FileCorpusRetriever：语料目录不存在 %s", self.root)
            return []
        out: list[tuple[str, str]] = []
        for p in sorted(self.root.rglob("*")):
            if p.suffix.lower() in (".txt", ".md") and p.is_file():
                out.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
        return out

    def search(self, query: str, k: int = 3) -> list[str]:
        self.calls.append((query, k))
        docs = self._docs()
        hits = [name for name, text in docs if query.lower() in text.lower()]
        if not hits:
            logger.warning("FileCorpusRetriever：query=%r 无命中（返回空）", query)
        return hits[:k]
