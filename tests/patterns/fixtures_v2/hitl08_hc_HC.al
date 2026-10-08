(defhitl-agent hitl08_hc
  :approval-policy (cost>100USD risk>=high pii)
  :escalation (slack "#ops-oncall" SLA 5min)
  :timeout 30min
  :audit-log (immutable-s3 bucket))
