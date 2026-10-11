"""examples.dist 子包标记。

examples/ 是常规包（含 __init__.py），其子目录必须同样有 __init__.py，
否则 Python 不把 examples.dist 当包解析 —— CI 报 No module named 'examples.dist'，
受影响用例：runtime/tests/test_srs_acceptance.py、runtime/tests/test_v2_smoke.py。
"""
