(defchain-agent doc-pipeline
  :steps ((:prompt "提取文档摘要" :out summary)
          (:prompt "基于摘要生成代码" :in summary :out code)))
