(defchain-agent wrong-doc-pipeline :context-policy (:memory-policy (:markdown-fs "/tmp/wrong.md" :layers (L0-Abstract) :auto-append #t)) :steps ((:prompt "S1" :out x)))
