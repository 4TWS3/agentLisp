(defdecomposition-agent decomp02_hc
  :subtasks ((ingest "数据接入") (clean "清洗") (analyze "分析"))
  :orchestrator (fan-out 4)
  :rollup (merge-by-timestamp))
