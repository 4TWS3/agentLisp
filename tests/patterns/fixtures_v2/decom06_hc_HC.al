(defdecomposer-agent decom06_hc
  :granularity per-paragraph
  :techniques (mdp-splitting llm-judged heuristic)
  :subagent-pool (worker-a worker-b worker-c)
  :merge weighted-vote)
