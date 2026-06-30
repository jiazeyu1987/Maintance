# 验证报告：测试服 DCC Codex 文件识别能力

## 目标

只读判断当前测试服务器是否可以用 Codex 识别 DCC 文件的项目名称、项目编码，并通过项目编码对应到 DCC 基础数据中的项目名称。

## 结果

`BLOCKED_FOR_FULL_CODEX_CONTENT_RECOGNITION`

测试服已经具备代码、库表和基础数据；文件名中包含唯一项目编码的场景可以由后端直接匹配并映射项目名称。但后端容器内没有可执行 Codex CLI，且缺少 Linux 下的 `yudao.dcc.project-code-recognition.codex-cli-command` 配置覆盖，因此文件内容级 Codex 识别不能视为当前已跑通。

## 证据

- 后端健康检查：`http://172.30.30.58:48081/actuator/health` 返回 `UP`。
- 主运行镜像：`intruoyi-backend:release-20260621-page-full-flow-mainmerge-v15`。
- 镜像代码：`/yudao-server/app.jar` 的嵌套 DCC jar 中包含识别服务、Codex CLI 客户端、配置类和控制器入口。
- 数据库结构：`dcc_project_code` 存在，`dcc_controlled_file` 存在识别回写字段。
- 基础数据：启用 DCC 项目编码记录 `248` 条，其中编码和名称完整 `242` 条。
- 受控文件：带源文件记录 `34667` 条。
- 直接识别样本：测试租户按最长唯一编码可命中文件 `923` 条。
- 阻塞点：宿主机有 `codex-cli 0.128.0`，但后端容器内未发现 `codex` / `codex.cmd`；compose 未配置识别命令覆盖；默认 `cmd.exe /c codex.cmd` 不适合 Linux 容器。

## 放行判断

- 文件名含唯一且足够明确项目编码：当前测试服可实现编码识别和编码到项目名称映射。
- 需要读取文件内容后由 Codex 判断项目名称/编码：当前测试服未跑通，需先把 Codex CLI 运行环境和 Spring 配置接入后端容器。
- 不能把短编码文件名命中作为高可信识别结论，短编码如 `IN`、`OC`、`EC` 在普通文件名中存在误识别风险。
