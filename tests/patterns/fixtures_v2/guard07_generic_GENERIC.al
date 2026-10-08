(defguardrails-safety-agent guard07_generic
  :audit (sampled 10%)
  :escalation (auto-block)
  :input-policy (pii-only)
  :output-policy (basic))
