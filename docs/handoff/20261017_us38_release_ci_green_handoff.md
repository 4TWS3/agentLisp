# US-38 交底：Release 工作流绿（真跑，非本地核对）

> 日期：2026-10-17
> 判据：Release 工作流绿

---

## 1. 结论

**真绿。** 推 tag \`v2.3.1\` 后 Release 工作流 7/7 job 全过：

| job | 结果 |
|---|---|
| Build macos-latest | success |
| Build ubuntu-latest | success |
| Build Windows x64 | success |
| Publish Docker Image | success |
| Publish GitHub Release | success |
| Publish to TestPyPI | skipped（非 -rc tag，按设计） |
| Publish to PyPI | skipped（未设 \`PUBLISH_PYPI\`） |

run id：\`39033945361\`。

---

## 2. 同时把 CI 修绿了

推 main 后 CI 7/7 green（run \`39036276756\`），含 Windows。

途中修了两个**只在 CI 暴露**的缺陷：

| 缺陷 | 修法 |
|---|---|
| CLI \`--version\` 测试写死 python/pyproject 的 0.1.0；装了 agentlisp 的环境打 2.3.1 | 测试改为与 \`__version__\` 比（同一解析规则） |
| 7 个脚本打印中文，Windows cp1252 下 UnicodeEncodeError | 脚本 stdout 强制 UTF-8 |

---

## 3. 产物

- GitHub Release \`v2.3.1\`
- Docker 镜像 \`ghcr.io/4tws3/agentlisp:v2.3.1\`

---

## 4. 未做

- 未发 PyPI（要 Trusted Publisher 或 token）。
- 未发 TestPyPI（非 -rc tag）。
