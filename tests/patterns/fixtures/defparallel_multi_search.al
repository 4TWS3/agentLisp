(defparallel-agent multi-search
  :branches ((search-a "来源 A") (search-b "来源 B"))
  :reducer aggregator-agent)
