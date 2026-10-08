(deffsm-agent fsm03_reverse
  :final (end)
  :transitions ((a go => end))
  :initial a
  :states (a end))
