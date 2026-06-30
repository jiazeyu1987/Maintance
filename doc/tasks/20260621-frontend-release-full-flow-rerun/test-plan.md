# Test Plan

## Test Cases

- test_case_id: TC-01
  mapped_task_ids:
    - T1
    - T2
  mapped_acceptance_ids:
    - AC-01
    - AC-05
  environment or setup: 本机维护仓任务文档与请求记录
  steps:
    - 检查旧任务已显式阻塞
    - 检查新任务已记录本次发布基线阻塞点
  expected_result: 不会在基线未明确时直接进入新的真实写入动作
  evidence: `task.md`、`request-analysis.md`、`execution-log.md`

- test_case_id: TC-02
  mapped_task_ids:
    - T2
  mapped_acceptance_ids:
    - AC-01
  environment or setup: 本机维护仓、业务前后端仓、运行控制台
  steps:
    - 核对维护仓/后端仓/前端仓工作树与目标基线
    - 记录 `experience-preflight`
  expected_result: 高风险动作前置条件与目标基线明确且可追溯
  evidence: `execution-log.md`

- test_case_id: TC-03
  mapped_task_ids:
    - T3
  mapped_acceptance_ids:
    - AC-02
  environment or setup: 运行控制台页面 + Playwright 真实页面操作
  steps:
    - 通过页面提交 build-release
    - 核对 operation、manifest、NAS 发布包
  expected_result: 候选包由页面真实动作生成并通过只读产物校验
  evidence: operation JSON/log、manifest、页面截图或快照记录

- test_case_id: TC-04
  mapped_task_ids:
    - T4
  mapped_acceptance_ids:
    - AC-02
    - AC-03
  environment or setup: 测试服 `172.30.30.58`
  steps:
    - 通过页面提交部署测试服
    - 核对远端 `.env`、运行镜像、健康与页面入口
  expected_result: 测试服运行态与 `releaseTag` 一致
  evidence: operation JSON/log、只读运行态输出

- test_case_id: TC-05
  mapped_task_ids:
    - T5
  mapped_acceptance_ids:
    - AC-02
  environment or setup: 运行控制台页面
  steps:
    - 通过页面选择恢复候选并提交 mark-tested
    - 核对结果元数据
  expected_result: 页面真实标记测试通过成功
  evidence: operation JSON/log、结果文件

- test_case_id: TC-06
  mapped_task_ids:
    - T6
  mapped_acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  environment or setup: 正式服
  steps:
    - 通过页面提交上线正式服
    - 核对远端 `.env`、运行镜像、健康、页面入口与受保护边界
  expected_result: 正式服运行态与边界全部通过
  evidence: operation JSON/log、只读运行态输出、边界查询结果

- test_case_id: TC-07
  mapped_task_ids:
    - T7
  mapped_acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  environment or setup: 备份服 `172.30.30.59`
  steps:
    - 通过页面提交上线备份服
    - 核对远端 `.env`、运行镜像、健康、页面入口与受保护边界
  expected_result: 备份服运行态与边界全部通过
  evidence: operation JSON/log、只读运行态输出、边界查询结果

- test_case_id: TC-08
  mapped_task_ids:
    - T8
  mapped_acceptance_ids:
    - AC-02
    - AC-03
    - AC-04
  environment or setup: 本机任务目录
  steps:
    - 汇总所有 execution/test evidence
    - 运行 task-closeout-cleanup 预览
  expected_result: 可明确证明本轮一次性走通，或明确记录阻塞点
  evidence: `execution-log.md`、`test-report.md`、收尾预览结果
