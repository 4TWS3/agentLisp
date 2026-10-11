(defrag-agent rag15_hc
  :priority-level 1
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
