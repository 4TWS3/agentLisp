"""agentlisp new：10 分钟跑通第一个 agent。

用法：
  python3 scripts/al_new.py /tmp/my-agent
  cd /tmp/my-agent && python3 run.py

生成物：一个 3 节点 .al（纯 DSL，无 Python handler）+ 一个 run.py。
目标是「从零到有输出」，不是「生成一个好 agent」。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "compiler" / "main.rkt"
RACKET = "racket"

AL = """(define-agent demo
  (:model :provider "openai" :name "deepseek-v4-flash" :temperature 0.2
          :system-prompt "你是示例助手。只基于给定事实回答，不编造。")
  (:tools (import-builtin read-file))
  (:context :memory-policy (:markdown-fs "./memory.md" :layers (L0-Abstract) :auto-append #f))
  (:state :fields ((facts :type dict)
                   (summary :type str)
                   (report :type str)))
  (:harness
    (:constrain :require-human-approval () :forbidden-commands ("rm -rf"))
    (:verify :json-schema #f :linter-check #f :test-runner "")
    (:correct :max-retries 1 :on-failure abort))
  (:workflow :entry facts
    :nodes ((facts :type computation
                   :body (hash "facts" (hash "revenue" 120000 "cost" 96000))
                   :output-fields (facts))
            (summary :type agent
                     :body (hash "summary"
                                 (llm (format "一句话总结这组数：~a" (hash-ref state "facts"))))
                     :output-fields (summary))
            (report :type computation
                    :body (hash "report" (format "结论：~a" (hash-ref state "summary" "")))
                    :output-fields (report)))
    :topology ((sequential (facts summary report)))))
"""

RUN = '''"""跑刚生成的 agent。"""
import importlib.util, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/Users/lee/products/agentLisp")

from runtime.langgraph_bridge import build_graph

spec = importlib.util.spec_from_file_location("demo", HERE / "agent.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
h = mod.DemoHarness()
out = build_graph(h.WORKFLOW, handlers={}, state_fields=h.STATE_FIELDS).invoke({})
print("facts :", out.get("facts"))
print("summary:", out.get("summary"))
print("report :", out.get("report"))
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="生成目录")
    args = ap.parse_args()
    d = Path(args.target).expanduser().resolve()
    d.mkdir(parents=True, exist_ok=True)
    (d / "agent.al").write_text(AL, encoding="utf-8")
    (d / "run.py").write_text(RUN, encoding="utf-8")

    cp = subprocess.run(
        [RACKET, str(MAIN), "-i", str(d / "agent.al"), "-o", str(d / "agent.py")],
        cwd=str(d),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if cp.returncode != 0:
        print(cp.stderr[-800:], file=sys.stderr)
        return 1
    print(f"[new] 已生成并编译：{d}")
    print(f"      下一步：cd {d} && python3 run.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
