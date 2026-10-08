(defexploration-agent explore10_generic
  :budget (max-trials 20)
  :search-space (depth 1..10)
  :rollout (epsilon-greedy eps=0.1)
  :pruning none)
