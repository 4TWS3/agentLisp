(defexploration-agent explore10_hc
  :search-space (hyperparam-range lr ("1e-5" "1e-2") batch (32 512))
  :budget (max-trials 200 max-time 2h wall)
  :pruning (median-stop 5%-ile after 5 trials)
  :rollout (ucb-exploration c=2.0))
