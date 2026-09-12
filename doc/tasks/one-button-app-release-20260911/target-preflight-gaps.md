# r15 目标只读检查覆盖缺口

状态：未通过。本报告只记录既有 r15 输入的离线诊断，不赋予 r15 或新 releaseTag 发布资格。

- 待验证检查：58
- 已通过：0
- 是否启动目标 SSH：false
- 失败码：TARGET_PREFLIGHT_MISSING
- 绑定计划：sha256:c98dd3f202040286a8234f8616526724789b3e46d886e31a1180069fc0ba0ea5

应优先核对已验证应用分支中的现有查询与 schema/menu 拆分；仅选择性融合仍适用的修复，保留当前新增代码。不能删除迁移、修改账本或更改标记来消除缺口。每个保留的待应用数据依赖均需有真实谓词和执行证据。

缺失的迁移检查文件（相对应用 `IntRuoyiBackend/sql/mysql/target-preflight/`）：

- `20260526_dcc_other_template_category.preflight.sql`
- `20260629_mes_smart_scheduling_role_scope.preflight.sql`
- `20260709_mes_rt000006_batch_record_mapping.preflight.sql`
- `20260716_mes_balloon_xlsx_route_00002_invalid_process_cleanup.preflight.sql`
- `20260717_mes_balloon_excel_device_workstation_binding.preflight.sql`
- `20260717_mes_invalid_process_reference_normalization.preflight.sql`
- `20260718_mes_puhui_schedule_admin_role_visibility.preflight.sql`
- `20260718_mes_route_version_bpm_notify_to_inbox.preflight.sql`
- `20260718_mes_route_version_withdraw_reopen_permission_menu.preflight.sql`
- `20260719_dcc_obsolete_form_policy_seed.preflight.sql`
- `20260720_edhr_release_void_form_policy_seed.preflight.sql`
- `20260720_mes_edhr_work_task_runtime_entitlement_backfill.preflight.sql`
- `20260720_mes_schedule_replan_form_policy_seed.preflight.sql`
- `20260721_batch_record_bpm_policy_seed.preflight.sql`
- `20260721_mes_route_version_publish_business_approval_policy_seed.preflight.sql`
- `20260721_mes_schedule_replan_approval_retire.preflight.sql`
- `20260722_edhr_release_form_policy_retire.preflight.sql`
- `20260721_form_template_obsolete_bpm_policy_seed.preflight.sql`
- `20260722_mes_route_creator_route_edit_permission_backfill.preflight.sql`
- `20260723_mes_route_form_business_approval_policy_backfill.preflight.sql`
- `20260723_mes_route_form_permission_rule_version_backfill.preflight.sql`
- `20260723_unify_form_action_policy_into_business_approval_policy.preflight.sql`
- `20260723_z_edhr_batch_void_business_policy_all_state.preflight.sql`
- `20260725_system_backup_plan_menu.preflight.sql`
- `20260728_mes_scheduler_route_flow_list_permission.preflight.sql`
- `20260728_fix_mdm_product_menu_utf8_name.preflight.sql`
- `20260728_user_list_access_role.preflight.sql`
- `20260729_dcc_product_catalog_remove_subsidiary_source.preflight.sql`
- `20260807_test_tenant1_all_role_permission_sync.preflight.sql`
- `20260808_mes_qa_optional_equipment_items.preflight.sql`
- `20260809_mes_team_leader_employee_scope_backfill.preflight.sql`
- `20260811_mes_process_pool_cleaning_wash_parameter_data.preflight.sql`
- `20260811_mes_process_pool_cleaning_process_parameter_data.preflight.sql`
- `20260811_mes_process_pool_uv1_metering_valid_parameter.preflight.sql`
- `20260811_mes_process_pool_uv2_two_device_runtime_config.preflight.sql`
- `20260811_mes_qa_pressure_pump_id_seed.preflight.sql`
- `20260812_mes_pqc_dcc_qa_c00_preflight.preflight.sql`
- `20260812_mes_pqc_dcc_qa_c00_backfill.preflight.sql`
- `20260812_mes_pqc_dcc_qa_c00_rollback.preflight.sql`
- `20260812_mes_process_pool_b04091_cleaning_temperature_label.preflight.sql`
- `20260812_mes_process_pool_b09353_cleaning_temperature_label.preflight.sql`
- `20260812_mes_qa_pressure_pump_idi_seed.preflight.sql`
- `20260818_mes_pressure_pump_same_name_item_convergence.preflight.sql`
- `20260829_mes_old_form_template_binding_switch.preflight.sql`
- `20260829_registration_certificate_management_menu_hierarchy.preflight.sql`
- `20260830_dcc_registration_certificate_associated_company_backfill.preflight.sql`
- `20260830_dcc_registration_certificate_notification_role_scope_backfill.preflight.sql`
- `20260830_mdm_company_scope_crud_menu.preflight.sql`
- `20260830_mes_process_pool_idi_device_parameter_rules.preflight.sql`
- `20260901_dcc_registration_certificate_change_submit_role_permission.preflight.sql`
- `20260901_dcc_registration_certificate_threshold_notify_template.preflight.sql`
- `20260901_mes_pqc_leader_nonconformance_review_permission.preflight.sql`
- `20260905_erp_kingdee_production_replenishment_list_sync.preflight.sql`
- `20260907_dcc_publication_notification.preflight.sql`
- `20260908_system_backup_evidence_export_permission.preflight.sql`
- `20260910_erp_finance_fenbeitong_assistant_menu.preflight.sql`
- `20260911_dcc_publish_direct_policy.preflight.sql`
- `20260911_dcc_retire_form_center_upload_entry.preflight.sql`
