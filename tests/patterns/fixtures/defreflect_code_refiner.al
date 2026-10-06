(defreflect-agent code-refiner
  :provider "anthropic" :model-name "claude-3-7-sonnet"
  :tools (bash pytest) :critic "检查代码逻辑漏洞" :max-retries 3)
