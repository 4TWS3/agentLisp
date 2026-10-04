# AgentLisp v2.0 需求 ↔ 测试 可追溯性矩阵 (Traceability Matrix)

> 生成来源：`pytest --junitxml` 导出结果 + `conftest.py` @req marker → property
> 
> 总计：87 个 Scenario，Passed=87，Failed=0，Skipped/Xfail=0

| SRS-ID | Scenario 数量 | Passed | Failed | Skipped/Xfail | 覆盖到的 Scenario 列表 |
| --- | ---: | ---: | ---: | ---: | --- |
| AC-3 | 2 | 2 | 0 | 0 | 「test_基于三条件_and_成功判定规则进行样本评估」、「test_评估新旧_agent_版本的_mcnemar_配对卡方统计显著性」 |
| FR-CHECK-0 | 1 | 1 | 0 | 0 | 「test_json_errors_shape_via_checker_rkt_source」 |
| FR-CHECK-1 | 7 | 7 | 0 | 0 | 「test_build_context_static_blocks_order_and_statusbar_role_system」、「test_compiler_structured_errors_mapped_to_exception_message_shapes」、「test_json_errors_kv_alignment_has_correct_hints_srs_id」、「test_kv_cache_静态前缀强对齐校验_err_kv_alignment_violation[(:context :auto)-(:model "claude-3-5")-FAIL-ERR_KV_ALIGNMENT_VIOLATION]」、「test_kv_cache_静态前缀强对齐校验_err_kv_alignment_violation[(:context :auto)-(:tools [bash])-FAIL-ERR_KV_ALIGNMENT_VIOLATION]」、「test_kv_cache_静态前缀强对齐校验_err_kv_alignment_violation[(:model "claude-3-5")-(:context :auto)-PASS-NONE]」 等 7 个 |
| FR-CHECK-2 | 1 | 1 | 0 | 0 | 「test_声明具副作用工具但缺少_harness_护栏_err_unguarded_tool_execution」 |
| FR-CHECK-3 | 1 | 1 | 0 | 0 | 「test_跨_agent_作用域工具命名冲突校验_err_context_leakage」 |
| FR-CORRECT-1 | 3 | 3 | 0 | 0 | 「test_correct_静默重试与_circuitbreaking_熔断[1-SILENT_RETRY_WITH_FEEDBACK]」、「test_correct_静默重试与_circuitbreaking_熔断[2-SILENT_RETRY_WITH_FEEDBACK]」、「test_correct_静默重试与_circuitbreaking_熔断[3-CIRCUIT_BREAK_TRIGGER_ASK_HUMAN]」 |
| FR-MAGT-1 | 3 | 3 | 0 | 0 | 「test_ac_2_fr_magt_1_scoped_worker_trajectory_not_leak_to_parent_build_context」、「test_ac_2_fr_magt_1_two_workers_trajectory_are_isolated_from_each_other」、「test_scopedworker_局部_trajectory_作用域隔离与_gc_原地清理」 |
| FR-MEM-1 | 5 | 5 | 0 | 0 | 「test_ac_2_fr_mem_1_emitter_generates_memory_fs_mount_code_and_prefix_tag」、「test_markdownfs_三层记忆_l0l1l2_渐进式加载[L0-SOUL.md \u5168\u91cf\u7075\u9b42\u7ea6\u675f + MEMORY.md L0 Abstract \u6458\u8981]」、「test_markdownfs_三层记忆_l0l1l2_渐进式加载[L1-L0 \u5185\u5bb9 + MEMORY.md L1 Section Overview \u6982\u89c8]」、「test_markdownfs_三层记忆_l0l1l2_渐进式加载[L2-L1 \u5185\u5bb9 + \u57fa\u4e8e URI/\u8d85\u94fe\u63a5\u6309\u9700\u60f0\u6027\u8c03\u53d6\u5168\u6587]」、「test_memory_fs_layers_constants_exist_and_basic_ops_ok」 |
| FR-RUN-1 | 6 | 6 | 0 | 0 | 「test_build_context_roles_are_system_prefix_then_dynamic_then_statusbar_system」、「test_harness_constrain_负面清单精确过滤[cat-cat /etc/shadow-BLOCKED-\u654f\u611f\u8bfb\u53d6\u547d\u4ee4\u7cbe\u51c6\u62e6\u622a]」、「test_harness_constrain_负面清单精确过滤[cat-ls category-ALLOWED-\u5355\u8bcd\u524d\u7f00\u4e0d\u8bef\u6740]」、「test_harness_constrain_负面清单精确过滤[rm -rf-mkdir /tmp/rm_rf_logs-ALLOWED-\u907f\u514d\u5b50\u4e32\u5339\u914d\u8bef\u6740]」、「test_harness_constrain_负面清单精确过滤[rm -rf-rm -rf /var/log-BLOCKED-\u5371\u9669\u5220\u9664\u547d\u4ee4\u7edd\u5bf9\u62e6\u622a]」、「test_harness_pipeline_event_order_via_statusbar」 |
| FR-RUN-2 | 10 | 10 | 0 | 0 | 「test_constrain_approval_blocks_git_push_when_listed_sanity」、「test_constrain_blocks_exact_forbidden_but_not_false_positive」、「test_constrain_token_boundary[cat-cat /etc/passwd-False]」、「test_constrain_token_boundary[cat-ls category-True]」、「test_constrain_token_boundary[git reset-describe about git reset usage-False]」、「test_constrain_token_boundary[git reset-git reset --hard HEAD-False]」 等 10 个 |
| FR-RUN-3 | 2 | 2 | 0 | 0 | 「test_ac_2_fr_run_3_workspace_root_path_escape_blocked」、「test_workspace_root_absolute_path_escape_and_semantic_arg_names」 |
| FR-RUN-4 | 3 | 3 | 0 | 0 | 「test_correct_on_failure_abort_is_reflected_in_trace_when_circuit_break」、「test_verify_failure_triggers_correct_then_circuit_breaker」、「test_完整_react_轨迹与离线质溯落盘」 |
| NFR-OBS-1 | 2 | 2 | 0 | 0 | 「test_ac_2_nfr_obs_1_otel_span_count_matches_turn_count」、「test_react_轮次与_harness_拦截事件导出为_opentelemetry_trace_span」 |
| NFR-PERF-1a | 4 | 4 | 0 | 0 | 「test_ac_2_nfr_perf_1a_static_bytes_ge_85pct_with_production_repair_agent」、「test_build_context_contract_with_status_bar_custom_items」、「test_kv_prefix_static_segment_ratio_ge_85pct_with_mock_llm」、「test_上下文物理组装严格按照_kv_cache_前缀优化布局」 |
| NFR-REL-1 | 2 | 2 | 0 | 0 | 「test_ac_2_nfr_rel_1_redis_checkpoint_default_ttl_ge_86390s」、「test_memory_checkpoint_default_is_memory_store_and_roundtrip」 |
| NFR-REL-2 | 1 | 1 | 0 | 0 | 「test_execution_trace_shape_has_required_fields」 |
| NFR-SEC-1a | 4 | 4 | 0 | 0 | 「test_workspace_root_路径逃逸与符号链接穿透双重防护[/etc/passwd-BLOCK-\u7edd\u5bf9\u8def\u5f84\u9003\u9038\u7edd\u4e0d\u901a\u8fc7]」、「test_workspace_root_路径逃逸与符号链接穿透双重防护[/workspace/sandbox/../../etc/shadow-BLOCK-\u76f8\u5bf9\u8def\u5f84 .. \u7a7f\u900f\u62e6\u622a]」、「test_workspace_root_路径逃逸与符号链接穿透双重防护[/workspace/sandbox/src/main.py-PASS-\u5de5\u4f5c\u533a\u5185\u6b63\u5e38\u8def\u5f84\u901a\u8fc7]」、「test_workspace_root_路径逃逸与符号链接穿透双重防护[/workspace/sandbox/symlink_to_outside-BLOCK-\u7b26\u53f7\u94fe\u63a5 (Symlink) \u7269\u7406\u6307\u5411\u5916\u9501\u6b7b]」 |
| NFR-SEC-1b | 2 | 2 | 0 | 0 | 「test_ac_2_nfr_sec_1b_require_approval_blocks_until_signal」、「test_status_bar_custom_wrapper_can_intercept_human_required_lifecycle」 |
| NFR-SEC-1c | 1 | 1 | 0 | 0 | 「test_sandbox_null_is_default_and_docker_sandbox_feature_not_installed_error_shape」 |
| IF-API-1 | 2 | 2 | 0 | 0 | 「test_gateway_smoke_import_or_feature_not_installed」、「test_通过_serversent_events_sse_实时流式推送推理轨迹」 |
| IF-SDK-1 | 1 | 1 | 0 | 0 | 「test_base_harness_v2_signature_accepts_all_required_keywords」 |
| IF-TEMPORAL-1 | 1 | 1 | 0 | 0 | 「test_敏感工具触发_temporal_人在回路_hitl_挂起与_signal_唤醒」 |
| (未映射 SRS-ID) | 23 | 23 | 0 | 0 | 「test_base_harness_mock_llm_completes」、「test_build_context_kv_order_and_status_bar_role」、「test_checkpoint_save_and_from_checkpoint_restore」、「test_cli_导出精准_srcloc_json_错误格式」、「test_constrain_blocks_exact_forbidden_but_not_false_positive」、「test_constrain_token_boundary[bash -c 'rm -rf /tmp/x'-rm -rf-True]」 等 23 个 |

## 说明

- `(未映射 SRS-ID)`：对应测试用例没有打上 @pytest.mark.req(...) / BDD feature 没有 @FR-CHECK-1 等 SRS tag。
- 与 `docs/spec/agentlisp_srs.md` 附录 B 的 Traceability Matrix 做交叉比对，即可判定「需求覆盖完备性」。
- Failed ≠ 0 的需求行：需要修复对应测试用例后再发版。
