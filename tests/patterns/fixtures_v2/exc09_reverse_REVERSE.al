(defexception-agent exc09_reverse
  :monitoring stdout
  :dead-letter /dev/null
  :retry-policy (none)
  :fallback raise)
