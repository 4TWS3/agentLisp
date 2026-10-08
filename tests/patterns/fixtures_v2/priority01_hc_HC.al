(defpriority-agent priority01_hc
  :priority-level 3
  :policies ((safety 0.9) (quality 0.8) (cost 0.6))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
