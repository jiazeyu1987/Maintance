# Execution Log: 维护仓发布链路支持 DCC 批量识别 5 worker

BDD: 测试服发布链路写入 DCC 识别 worker-count -> Given 构建测试服 runtime env / When 未显式覆盖 DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT / Then `.env` 写入默认值 5，并由 compose 传入后端 `yudao.dcc.project-code-recognition.worker-count`。
GREEN: experience-preflight -> PASS，已读取 PowerShell/发布/服务器门禁；本阶段只修改维护仓本机文件，不执行测试服发布或重启。

RED: python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q -> FAIL，维护仓旧发布合同未写入 DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT，compose 未向后端透传 worker-count。
GREEN: python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q -> PASS，维护仓发布链路已写入 DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT，compose 已透传 worker-count。
GREEN: publish-chain-boundary -> PASS，本阶段只补维护仓发布链路配置和合同测试，未执行测试服发布、重启、正式服或备份服动作。
BLOCKER: test-server-five-worker-runtime -> 当前测试服务器 IMAGE_TAG=release-20260701-1720-message-text-fix，远端 .env 缺少 DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT=5，backend 启动参数缺少 project-code-recognition.worker-count，运行 jar 不含新增并发 worker 代码；已按 fail-fast 阻止启动产品识别，需先发布已提交的后端与维护仓发布链路改动到测试服。
