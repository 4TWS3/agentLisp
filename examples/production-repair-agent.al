;; =========================================================================
;; AgentLisp v2.0 SRS §6 生产级样例：production-repair-agent.al
;; 严格对齐：spec §3 EBNF 五大块 + §4 三条不可变 ERR_ + §6 验收 τ²-bench 代码修复场景
;; 预期：`racket compiler/main.rkt -i examples/production-repair-agent.al --check-only`
;;       必须 exit 0（不触发 ERR_KV_ALIGNMENT_VIOLATION / ERR_UNGUARDED_TOOL_EXECUTION
;;       / ERR_CONTEXT_LEAKAGE 三条错误码）
;; =========================================================================

(defagent production-repair-agent
  ;; ---- Static Block（KV Cache 前缀对齐：静态段必须在前） -------------------
  (:model
   :provider           "anthropic"
   :name               "claude-3-5-sonnet-20241022"
   :temperature        0.2
   :system-prompt       #<<EOF
你是一名精通 Python / TypeScript / Rust 的代码修复 Agent。
工作流程（严格遵守，不得跳步）：
  (1) 读取 failing pytest 输出（Trajectory 第 1 条 observation）
  (2) 在 workspace_root=/app 内定位出错源码文件（调用 read-file / grep-builtin）
  (3) 通过 linter-check 先过语法与 import 检查
  (4) 生成 patch（write-md / apply-patch-builtin），然后重新跑 test-runner = pytest tests/
  (5) 若连续 2 次 pytest 未全绿：自动触发 reviewer-agent = "judge"（拓扑 judge-driven）
  (6) 最终返回 FINAL_ANSWER = 修复后的 diff + pytest 全绿日志摘要
工具约束（Harness 一等控制流）：
  * 所有需要写文件 / 改 git 的操作（write-md / git-push / apply-patch-builtin）
    必须先经过 Constrain.require_human_approval 门控，
    父 Agent orchestrator 将在 HITL 后触发 SIGNAL_APPROVE
  * 工作区逃逸（任何绝对路径、../ 相对路径）由 workspace_root 门控拦截
EOF
)

  (:tools
   ;; builtins：read-file 读；bash 执行 pytest；git-push 部署
   (import-builtin read-file bash git-push apply-patch-builtin grep-builtin)
   ;; MCP：VSCode LSP（诊断）+ 代码审查
   (import-mcp "stdio://./tools/mcp_vscode_lsp.py")
   (import-mcp "http+unix://%2Frun%2Fuser%2F1000%2Fmcp-reviewer.sock/")
   ;; 自定义工具：写 Markdown 报告
   (define-tool write-md
     ((path string) (content string))            ; input schema
     ((ok boolean?) (saved_bytes number?))))     ; output schema

  ;; ---- Dynamic Block（KV Cache：动态段必须在静态段之后） -----------------
  (:context
   :memory-policy (:markdown-fs "./docs/memory"
                                  :layers (L0-Abstract L1-Overview L2-FullText)
                                  :auto-append #t)
   :skills ("python-debugging" "typescript-linting" "rust-cargo-fmt" "dacf-ths-criteria")
   :status-bar (:step-count        #t
                :current_branch    #t
                :test_status       #t
                :time_tracker      #t
                :todo_list         #t
                :custom            ((workspace_root       "/app")
                                    (dataset_tag          "τ²-bench-v1.0")
                                    (fix_rate_target      "0.90")))
   :compression :rolling-summary-window-20)

  ;; ---- Harness Block（Harness 一等控制流：三重管道 + 审批 + 沙箱锁） --------
  (:harness
   (:constrain
    :require-human-approval   (write-md git-push apply-patch-builtin)
    :forbidden-commands       ("rm -rf"          "git reset --hard" "shutdown -h now"
                               "curl | bash"      "wget | sh"        "chmod -R 777")
    :workspace-root           "/app"
    :_matching                'token_boundary)
   (:verify
    :json-schema              #t
    :linter-check             #t
    :test-runner              "pytest tests/ --maxfail=1 -q"
    :reviewer-agent           "judge")
   (:correct
    :max-retries      3
    :circuit-breaker  5
    :on-failure       ask-human))

  ;; ---- Multi-Agent Block（词法作用域 scoped-worker；父子 define-tools 不重名；
  ;;      topology=judge-driven；对应 SRS §3 MultiAgentBlock EBNF） --------------
  (:multiagent
   :topology judge-driven
   :workers
   (
    ;; (A) 代码 Lint 子 worker：工具名 = lint-only-*，不与父重名
    (scoped-worker lint-only-worker
      (:model
       :provider    "mock"
       :name        "lint-mock"
       :temperature 0.0
       :system-prompt "你只负责做 lint 检查，不修改文件。")
      (:tools (import-builtin bash read-file)
             (define-tool lint-py ((path string)) ((ok boolean?) (errors list?))))
      (:harness (:constrain :workspace-root "/app" :_matching 'token_boundary)
                (:verify  :linter-check #t)
                (:correct :max-retries 2 :circuit-breaker 3 :on-failure abort)))

    ;; (B) 测试 Runner 子 worker：工具名 = run-tests-worker-only-*
    (scoped-worker run-tests-worker
      (:model
       :provider    "mock"
       :name        "pytest-mock"
       :temperature 0.0
       :system-prompt "你只负责执行 test-runner 命令并输出 pytest 摘要。")
      (:tools (import-builtin bash)
             (define-tool run-tests-worker-only-pytest
               ((marker string) (timeout_ms number?))
               ((exit_code number?) (summary string) (failed_tests list?))))
      (:harness (:constrain :workspace-root "/app" :_matching 'token_boundary)
                (:verify  :test-runner "pytest tests/ -q")
                (:correct :max-retries 3 :circuit-breaker 5 :on-failure fallback-model)))

    ;; (C) 评审 Judge：不直接使用父工具，只暴露 reviewer-only-*
    (scoped-worker judge
      (:model
       :provider    "anthropic"
       :name        "claude-3-5-sonnet-20241022"
       :temperature 0.0
       :system-prompt "你是终审法官：对修复结果做 DCAF-THS 三维打分（稳定性/重复性/迁移性），0.8 以下打回重写。")
      (:tools (define-tool reviewer-only-score
               ((patch_diff string) (pytest_stdout string))
               ((ths_stability number?) (ths_repeatability number?) (ths_migration number?)
                (overall_score number?) (feedback string))))
      (:harness (:constrain)
                (:verify  :reviewer-agent "judge")
                (:correct :max-retries 2 :circuit-breaker 3 :on-failure ask-human)))
   )))
