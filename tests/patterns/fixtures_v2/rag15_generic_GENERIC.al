(defrag-agent rag15_generic
  :priority-level 1
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
