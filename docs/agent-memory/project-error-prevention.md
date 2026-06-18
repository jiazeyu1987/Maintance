# Project Error Prevention Memory

- 发布验证不要只看本机源码或单点健康检查；必须按“源码进入唯一发布源头 -> 发布产物验证 -> 目标环境真实运行态”三层确认，环境差异和服务器暴露的问题要补成门禁。
- 环境发布流程前先预检 Dockerfile 基础镜像、迁移策略门禁和 Maven target/jar 锁；失败不生成可部署包；证据: 20260617-release
- 任务提交前跑 TDD 钩子；execution-log 用裸 RED/GREEN，sql/mysql 变更配 script/tests；证据: 20260617-release
- 环境发布验证不能只看健康；必须核 operation SUCCESS、manifest、远端 IMAGE_TAG/镜像、迁移状态和真实浏览器入口；证据: 20260617-release
