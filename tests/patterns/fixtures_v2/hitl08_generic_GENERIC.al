(defhitl-agent hitl08_generic
  :timeout 1h
  :approval-policy (any-cost>50)
  :audit-log local
  :escalation email)
