(defdecomposition-agent decomp02_generic
  :orchestrator (fan-out 2)
  :rollup concat
  :subtasks ((a "A")))
