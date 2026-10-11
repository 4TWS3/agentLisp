(defgoal-agent goal20_hc
  :priority-level 6
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
