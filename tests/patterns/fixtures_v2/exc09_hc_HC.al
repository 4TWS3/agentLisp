(defexception-agent exc09_hc
  :fallback (degrade-to-cache retry-best-effort)
  :retry-policy (exponential-backoff base 2s max 10)
  :dead-letter (s3 bucket + dlq-notify)
  :monitoring (datadog alarm-threshold 5/5min))
