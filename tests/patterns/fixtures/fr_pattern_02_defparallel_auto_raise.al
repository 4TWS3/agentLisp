(defparallel-agent wrong-ms :context-policy (:memory-policy (:markdown-fs "/tmp/w.md" :layers (L0-Abstract))) :branches ((a "A")) :reducer r)
