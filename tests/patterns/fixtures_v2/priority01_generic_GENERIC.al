(defpriority-agent priority01_generic
  :routing-table ((urgent => fast-path))
  :priority-level 2
  :policies ((cost 0.9)))
