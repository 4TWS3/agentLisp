(defrouter-agent ops-gateway
  :model ("openai" "gpt-5.6")
  :routes ((:intent 'db-query  => db-worker)
           (:intent 'net-debug => net-worker)))
