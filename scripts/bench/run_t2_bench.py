"""
AgentLisp v2.0 τ²-bench 端到端基准评估与 McNemar 卡方统计检验脚本 (scripts/bench/run_t2_bench.py)
符合 SRS AC-3 规约：
1. 三条件 AND 成功判定 (Runtime Error Rate = 0 AND Pytest 100% PASS AND Rubric >= 0.8)
2. 计算 McNemar 统计量 chi2 = (|b - c| - 1)^2 / (b + c) 与 p-value
"""

import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("AgentLisp.T2Bench")


class T2BenchEvaluator:
    def __init__(self, dataset_doi: str = "t2-bench@v1.0"):
        self.dataset_doi = dataset_doi

    def evaluate_sample(self, sample_id: str, execution_result: dict[str, Any]) -> bool:
        """
        三条件 AND 逻辑成功判定:
        Condition 1: 无未捕获语法错或运行时 Exception (Runtime Error Rate = 0)
        Condition 2: pytest 单元测试 100% 绿色通过 (Environment Assertion PASS)
        Condition 3: LLM Code Reviewer 打分 >= 0.8 (Rubric >= 0.8)
        """
        cond1 = execution_result.get("runtime_error_rate", 1.0) == 0.0
        cond2 = execution_result.get("pytest_passed", False) is True
        cond3 = execution_result.get("rubric_score", 0.0) >= 0.8

        success = cond1 and cond2 and cond3
        logger.info(
            f"📊 Sample '{sample_id}' Evaluation -> Cond1(ErrorFree)={cond1}, Cond2(Pytest)={cond2}, Cond3(Rubric={execution_result.get('rubric_score')}): Final={success}"
        )
        return success

    @staticmethod
    def calculate_mcnemar_test(contingency_matrix: tuple[int, int, int, int]) -> dict[str, Any]:
        """
        计算 McNemar 统计量:
        Matrix shape:
                   Model B Success    Model B Fail
        Model A Success      a               b
        Model A Fail         c               d

        chi2 = (|b - c| - 1)^2 / (b + c)
        """
        a, b, c, d = contingency_matrix
        discordant = b + c
        if discordant == 0:
            return {
                "chi2": 0.0,
                "p_value": 1.0,
                "significant": False,
                "note": "No discordant pairs",
            }

        chi2 = ((abs(b - c) - 1) ** 2) / float(b + c)

        # 自由度为 1 的卡方分布近似 (临界值 3.841 对应 p < 0.05)
        p_significant = chi2 > 3.841

        return {
            "chi2": round(chi2, 4),
            "contingency_matrix": {"a": a, "b": b, "c": c, "d": d},
            "p_significant_p_lt_005": p_significant,
            "interpretation": "Statistically Significant Difference (p < 0.05)"
            if p_significant
            else "No Statistically Significant Difference",
        }


if __name__ == "__main__":
    print("=== AgentLisp τ²-bench 评估与 McNemar 统计检验 ===")
    evaluator = T2BenchEvaluator()

    # 测试样例判定
    mock_sample_res = {"runtime_error_rate": 0.0, "pytest_passed": True, "rubric_score": 0.92}
    is_success = evaluator.evaluate_sample("sample-001", mock_sample_res)
    assert is_success is True

    # 测试 McNemar 配对检验计算
    # 例如：100 个样本中，b=2 (A胜B败), c=15 (B胜A败)
    mcnemar_res = evaluator.calculate_mcnemar_test((70, 2, 15, 13))
    print("McNemar 统计结果:", mcnemar_res)
    print("✅ τ²-bench 评估模块运行测试成功！")
