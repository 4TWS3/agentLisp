(defresource-aware-agent resrc19_hc
  :priority-level 5
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
