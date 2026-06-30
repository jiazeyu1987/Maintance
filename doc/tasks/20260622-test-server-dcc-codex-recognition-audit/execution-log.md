# 执行日志

- GREEN: experience-preflight -> PASS，用户明确要求判断测试服务器当前能力；本任务限定为测试服只读核验，不发布、不重启、不写数据库、不登录写入 E2E。
- BDD: 测试服运行版本包含识别能力 -> Given 测试服后端运行镜像对应的代码提交 / When 核对提交或发布标签 / Then 能判断 DCC 识别实现是否已部署。
- BDD: 产品编码可对应产品名称 -> Given 测试服 DCC/Mdm 基础数据存在产品编码和名称映射 / When 查询真实基础数据 / Then 能确认识别出的编码可回填产品名称。
- BDD: 缺少部署或数据时必须阻塞 -> Given 测试服缺少代码、配置或基础数据 / When 核验能力 / Then 报告具体缺口和影响。
- GREEN: local-code-audit -> PASS，本机后端 `int_main` 存在 DCC 识别服务、Codex CLI 客户端、配置类、控制器入口和单元测试；实现路径为先按源文件名匹配唯一最长项目编码，匹配不到再读取源文件内容并调用 Codex CLI。
- GREEN: test-server-health -> PASS，`http://172.30.30.58:48081/actuator/health` 返回 `{"status":"UP"}`。
- GREEN: test-server-runtime-image -> PASS，测试服主容器为 `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v15` 与 `intruoyi-frontend:release-20260621-page-full-flow-mainmerge-v15`。
- GREEN: test-server-runtime-code -> PASS，主后端容器 `/yudao-server/app.jar` 的嵌套 `BOOT-INF/lib/yudao-module-dcc-2026.04-SNAPSHOT.jar` 中存在 `DccControlledFileProjectCodeRecognitionServiceImpl`、`DccProjectCodeCodexCliClientImpl`、`DccProjectCodeRecognitionProperties` 与 `DccControlledFileController.class`，并包含 `recognize-project-code` / `project-code-recognition` 字符串。
- GREEN: test-server-database-schema -> PASS，测试服库存在 `dcc_project_code`，`dcc_controlled_file` 存在 `dcc_project_code_id`、`project_code_recognition_type`、`project_code_recognition_text`、`product_code`、`product_name`。
- GREEN: test-server-basic-data -> PASS，`dcc_project_code` 启用记录 `248` 条，`tenant_id=122` 与 `tenant_id=1` 各 `124` 条，非空编码与名称完整记录 `242` 条。
- GREEN: test-server-controlled-files -> PASS，测试服 `dcc_controlled_file` 带源文件记录 `34667` 条，已有识别回写记录 `1` 条。
- GREEN: filename-code-path-sample -> PASS，按测试租户和当前代码的“最长且唯一项目编码”规则，文件名可直接命中的受控文件计数为 `923`；样本同时暴露短编码误识别风险，例如 `INT/...` 文件名会命中短编码 `IN`。
- BLOCKER: codex-content-recognition-runtime -> 后端容器内未发现 `codex` / `codex.cmd` 可执行入口，`docker-compose.yml` 未配置 `yudao.dcc.project-code-recognition.codex-cli-command` 覆盖项；代码默认值为 Windows 命令 `cmd.exe /c codex.cmd`，不适配当前 Linux 后端容器。影响：文件名不能唯一识别时，真实内容级 Codex 识别无法判定为测试服已跑通。
