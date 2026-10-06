(defplanner-agent deep-researcher
  :model ("anthropic" "claude-3-7-sonnet")
  :planner-prompt "将研究目标分解为 3-5 个步骤"
  :executor-tools (web-search read-pdf))
