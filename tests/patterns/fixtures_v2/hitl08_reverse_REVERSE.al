(defhitl-agent hitl08_reverse
  :audit-log memory
  :timeout 10s
  :escalation none
  :approval-policy (manual-all))
