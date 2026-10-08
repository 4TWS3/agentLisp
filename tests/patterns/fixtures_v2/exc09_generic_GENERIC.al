(defexception-agent exc09_generic
  :retry-policy (linear 1s max 3)
  :dead-letter local-dir
  :fallback default
  :monitoring prometheus)
