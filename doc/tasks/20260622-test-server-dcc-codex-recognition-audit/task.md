# 任务：测试服 DCC Codex 文件产品识别能力核验

## 任务目标

只读核验当前测试服务器是否已经具备用 Codex 识别 DCC 文件产品名称、产品编码，以及通过产品编码对应产品名称的能力。

## 当前状态

COMPLETED：已完成测试服只读核验；测试服具备 DCC 基础数据、识别接口代码和文件名编码直连识别能力，但后端容器内缺少可执行 Codex CLI / Linux 命令配置，无法确认内容级 Codex 识别当前可跑通。

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
- `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
- `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
- 强制门禁摘录：
  - 测试服检查必须明确目标主机、目录、容器和授权范围。
  - 本任务只读核验测试服，不做发布、重启、备份、恢复、回滚、数据库写入或对象存储写入。
  - 缺少测试服运行版本、基础数据、配置或真实文件数据时必须直接报告影响，不用 mock 或本机结果替代测试服结论。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否
- `是否从根因和长期维护角度解决`：是，通过运行版本、配置、数据库基础数据和接口/日志能力判断测试服真实状态。
- `是否存在临时补丁或绕过`：否

## BDD 场景

- `BDD: 测试服运行版本包含识别能力 -> Given 测试服后端运行镜像对应的代码提交 / When 核对提交或发布标签 / Then 能判断 DCC 识别实现是否已部署。`
- `BDD: 产品编码可对应产品名称 -> Given 测试服 DCC/Mdm 基础数据存在产品编码和名称映射 / When 查询真实基础数据 / Then 能确认识别出的编码可回填产品名称。`
- `BDD: 缺少部署或数据时必须阻塞 -> Given 测试服缺少代码、配置或基础数据 / When 核验能力 / Then 报告具体缺口和影响。`

## 里程碑

1. 建立只读核验任务台账与门禁。`DONE`
2. 核对本机代码中的 DCC 识别能力边界。`DONE`
3. 只读核对测试服运行版本、配置和基础数据。`DONE`
4. 给出测试服是否可实现的结论。`DONE`

## 预期验证

- `git log` / `rg` 只读核对本机 DCC 识别实现
- 测试服 `/actuator/health`
- 测试服运行标签 / 镜像 / 容器只读检查
- 测试服数据库基础数据只读查询

## 核验结论

- 测试服后端健康检查为 `UP`，主后端镜像为 `intruoyi-backend:release-20260621-page-full-flow-mainmerge-v15`。
- 测试服镜像内包含 `DccControlledFileProjectCodeRecognitionServiceImpl`、`DccProjectCodeCodexCliClientImpl`、`DccProjectCodeRecognitionProperties` 与 `/recognize-project-code` 控制器入口。
- 测试服数据库存在 `dcc_project_code`，并且 `dcc_controlled_file` 已具备 `dcc_project_code_id`、`project_code_recognition_type`、`project_code_recognition_text`、`product_code`、`product_name` 字段。
- 测试服 DCC 基础数据共 `248` 条启用记录，测试租户 `tenant_id=122` 与芋道租户 `tenant_id=1` 各 `124` 条；其中 `242` 条具备非空项目编码和项目名称。
- 测试租户中按当前代码的“文件名包含最长且唯一项目编码”规则，可直接命中的受控文件样本计数为 `923` 条；这类识别不依赖 Codex CLI。
- 测试服宿主机存在 `codex-cli 0.128.0`，但主后端容器内未发现 `codex` / `codex.cmd` 可执行入口，且 `docker-compose.yml` 未配置 `yudao.dcc.project-code-recognition.codex-cli-command` 覆盖项。
- 代码默认命令为 `cmd.exe /c codex.cmd`，该默认值适合 Windows 本机，不适合 Linux 后端容器；因此当前测试服不能判定为“Codex 内容识别已全部跑通”。
- 文件名直接识别对短编码存在误识别风险，例如 `INT/...` 文件名可命中短编码 `IN`，因此不能把文件名命中样本等同于高可信内容识别。

## 最终状态

`COMPLETED`
