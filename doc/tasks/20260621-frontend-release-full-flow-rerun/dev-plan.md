# Dev Plan

## Tasks

- task_id: T1
  title: 收口旧任务并建立本轮制品
  objective: 显式阻塞上一未完成任务，创建本轮任务文档、分析、计划、测试计划和状态文件。
  dependency_ids: []
  affected_paths:
    - doc/tasks/20260621-backup-server-backup-restore-rehearsal/task.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/
    - docs/request-command-log.md
  write_scope:
    - doc/tasks/20260621-backup-server-backup-restore-rehearsal/
    - doc/tasks/20260621-frontend-release-full-flow-rerun/
    - docs/request-command-log.md
  acceptance_ids:
    - AC-01
    - AC-05
  validation_steps:
    - 检查旧任务已从 `IN_PROGRESS` 改为显式 `BLOCKED`
    - 检查本轮任务目录和必需制品已创建
  done_definition: 旧任务状态已收口，本轮任务制品齐全且记录了当前阻塞。

- task_id: T2
  title: 明确发布基线并完成执行前 preflight
  objective: 明确本轮到底是重跑当前基线还是以既有 v6 证据为准；若重跑，则确认维护仓/业务仓/运行控制台基线并记录 `experience-preflight`。
  dependency_ids:
    - T1
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/task.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/task-state.json
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/
  acceptance_ids:
    - AC-01
    - AC-05
  validation_steps:
    - 任务文档中记录明确发布基线
    - `execution-log.md` 中记录 `GREEN: experience-preflight -> PASS` 或保留阻塞原因
  done_definition: 只有在发布基线明确且 preflight 通过后，T3-T8 才可进入 ready。

- task_id: T3
  title: 页面构建发布包
  objective: 通过页面真实执行 build-release，并核验候选包与 manifest。
  dependency_ids:
    - T2
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  acceptance_ids:
    - AC-02
  validation_steps:
    - 页面提交 build-release
    - 记录 operation、manifest、NAS 发布包证据
  done_definition: 页面构建成功且候选包核验通过。

- task_id: T4
  title: 页面部署测试服
  objective: 通过页面真实执行 deploy-release(test) 并完成测试服运行态核验。
  dependency_ids:
    - T3
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  acceptance_ids:
    - AC-02
    - AC-03
  validation_steps:
    - 页面提交测试服部署
    - 核远端 `.env`、镜像、健康检查与前端入口
  done_definition: 测试服真实部署成功且运行态核验通过。

- task_id: T5
  title: 页面标记测试通过
  objective: 通过页面真实执行 mark-tested，并核验恢复候选与测试结论落地。
  dependency_ids:
    - T4
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  acceptance_ids:
    - AC-02
  validation_steps:
    - 页面选择恢复候选并提交 mark-tested
    - 核 operation 与结果元数据
  done_definition: 页面标记测试通过成功且 required metadata 落地。

- task_id: T6
  title: 页面上线正式服
  objective: 通过页面真实执行 deploy-release(prod) 并完成正式服运行态与边界核验。
  dependency_ids:
    - T5
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  validation_steps:
    - 页面提交正式服上线
    - 核正式服 `.env`、镜像、健康、页面入口与受保护边界
  done_definition: 正式服真实部署成功且边界核验通过。

- task_id: T7
  title: 页面上线备份服
  objective: 通过页面真实执行 deploy-release(backup) 并完成备份服运行态与边界核验。
  dependency_ids:
    - T6
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
  acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  validation_steps:
    - 页面提交备份服上线
    - 核备份服 `.env`、镜像、健康、页面入口与受保护边界
  done_definition: 备份服真实部署成功且边界核验通过。

- task_id: T8
  title: 收尾与结论
  objective: 汇总一次性走通证据，更新测试报告，执行收尾预览并整理结论。
  dependency_ids:
    - T7
  affected_paths:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/task.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/execution-log.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/test-report.md
    - doc/tasks/20260621-frontend-release-full-flow-rerun/task-state.json
  write_scope:
    - doc/tasks/20260621-frontend-release-full-flow-rerun/
  acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  validation_steps:
    - 汇总所有 operation 与只读核验证据
    - 运行 task-closeout-cleanup 预览
  done_definition: 本轮结论、测试报告和状态文件全部更新，能清楚证明通过或阻塞。
