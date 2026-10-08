(defexploration-agent explore10_reverse
  :rollout random
  :pruning none
  :budget (max-time 10min)
  :search-space full-grid)
