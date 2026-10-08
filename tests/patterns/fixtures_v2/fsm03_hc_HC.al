(deffsm-agent fsm03_hc
  :states (idle running done error)
  :initial idle
  :final (done error)
  :transitions ((idle start => running) (running ok => done) (running bad => error)))
