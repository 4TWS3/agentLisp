;; AgentLisp v2.0 最小示例：文档修复 Agent
;; ----------------------------------------------------------
;; 用法：
;;   racket compiler/main.rkt -i examples/repair_agent.al -o examples/dist/repair_agent.py

(define-tool read-file
  #:description "读取本地 Markdown 文件"
  #:input  #hash((path . string?))
  #:output #hash((content . string?)))

(define-tool patch-text
  #:description "对文本做结构化 patch（按 section 覆盖）"
  #:input  #hash((path . string?) (section . string?) (new_content . string?))
  #:output #hash((patched . boolean?) (path . string?)))

(define-tool write-back
  #:description "将内容写回文件（保留版本记录）"
  #:input  #hash((path . string?) (content . string?))
  #:output #hash((ok . boolean?)))

(define-harness RepairHarness
  #:base ReActHarness
  #:react #hash((max_turns . 20)))

(define-agent document-repairer
  #:purpose "按 DCAF L0/L1/L2 规则修复政务文档"
  #:tools (read-file patch-text write-back)
  #:workflows
  ((define-workflow repair-md
     #:triggers (manual watch)
     #:steps
     ((define-step s1-read
        (atomic read-doc read-file path "input/doc.md")
        #:next s2-patch)
      (define-step s2-patch
        (atomic apply patch-text path "input/doc.md" section "项目背景" new_content "TODO")
        #:next s3-write)
      (define-step s3-write
        (atomic save write-back path "input/doc.md" content "$.results.s2-patch.patched")
        #:next #f
        #:when #t)))))
