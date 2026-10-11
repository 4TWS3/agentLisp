(deflearning-agent learn18_reverse
  :priority-level 4
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
