# language: zh-CN
功能: τ²-bench 端到端基准评估与 McNemar 统计显著性校验 (AC-3)
  作为 质量评估与持续进化框架
  必须支持重放 τ²-bench 数据集、执行环境真值断言与配对 McNemar 检验

  背景:
    假如 已经加载数据集 t2-bench@v1.0
    并且 评估套件集成了 Pytest 真值验证器与 LLM-as-a-Judge 打分器

  @AC-3 @T2-Bench-Evaluation
  场景: 基于三条件 AND 成功判定规则进行样本评估
    假如 测试样本 "repair-task-042" 执行完成
    当 评估引擎执行三条件 AND 逻辑判定:
      | 1. 无语法错/未捕获异常 (Runtime Error Rate = 0) |
      | 2. pytest 单元测试 100% 绿色通过 (Environment Assertion PASS) |
      | 3. Code Reviewer 打分 >= 0.8 (LLM-as-a-Judge Rubric) |
    那么 样本 "repair-task-042" 的最终评估判定结果应当为 "SUCCESS"

  @AC-3 @McNemar-Test
  场景: 评估新旧 Agent 版本的 McNemar 配对卡方统计显著性
    假如 收集到了 旧版本 (A) 与 新版本 (B) 在 100 个 τ²-bench 样本上的二元结果矩阵 (Contingency Matrix)
    当 计算 McNemar 卡方统计量 chi2 = (|b - c| - 1)^2 / (b + c)
    并且 自由度为 1 的 p-value < 0.05
    那么 系统判定新版本相比旧版本具备统计学上的显著提升 (Statistically Significant)
