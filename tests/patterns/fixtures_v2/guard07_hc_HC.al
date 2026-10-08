(defguardrails-safety-agent guard07_hc
  :input-policy (pii-filter prompt-injection-detect)
  :output-policy (toxicity-classifier hallucination-rate)
  :audit (full-trace retention 90d)
  :escalation (human-on-threshold 0.85))
