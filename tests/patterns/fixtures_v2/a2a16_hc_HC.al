(defa2a-agent a2a16_hc
  :priority-level 2
  :policies ((safety 0.9) (quality 0.8))
  :routing-table ((urgent => fast-path) (batch => slow-path)))
