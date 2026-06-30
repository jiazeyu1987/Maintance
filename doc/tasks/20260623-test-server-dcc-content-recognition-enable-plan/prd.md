# PRD：测试服 DCC 内容级 Codex 识别跑通

## Purpose and Scope

当前测试服后端代码、数据库与直连识别能力已具备，但内容级 Codex 识别仍未跑通。只读核验显示：

- 宿主机已有 `codex-cli 0.128.0`
- 业务后端仓的测试服发布脚本/compose 已预留：
  - `DCC_PROJECT_CODE_CODEX_CLI_COMMAND`
  - `DCC_PROJECT_CODE_CODEX_HOME`
  - `/opt/intruoyi/runtime/tools/codex`
  - `/opt/intruoyi/runtime/backend-codex-home`
- 维护仓当前 `ops/deploy/int-ruoyi-test/docker-compose.yml` 未携带同样的 DCC Codex 运行时合同

本任务目标是修复维护仓发布链路，使测试服通过正式发布入口重建后，backend 容器能够真实执行 Codex CLI 完成内容级识别。

## Actors

- 发布操作者：通过维护仓发布链路重建测试服 backend
- 文控用户：在测试服 DCC 页面点击“识别基础信息”
- 测试服 backend 容器：读取源文件内容并调用 Codex CLI
- 维护仓发布链路：负责把运行时命令、挂载和 `CODEX_HOME` 带到容器中

## Requirements

1. 维护仓 `publish-int-ruoyi.ps1` 必须显式支持 DCC Codex CLI 命令和 `CODEX_HOME` 相关环境变量。
2. 维护仓 `docker-compose.yml` 必须把 DCC Codex 命令、`CODEX_HOME` 和运行时挂载传入 backend 容器。
3. 测试服 backend 容器内必须能执行配置的 Codex 命令，并读取 `backend-codex-home` 中的认证配置。
4. 若运行时命令、挂载、认证或可执行文件缺失，发布后验证必须显式失败，不得仅以健康检查 `UP` 判定成功。
5. 最终验收必须证明真实样本走到了“读取文件内容 -> Codex 判断 -> 回写结果”的路径，而不是文件名快捷路径。
6. 任何认证文件、API key 或秘钥内容都不得入仓；只能以远端受控运行时方式落地。
7. 若 backend 共享配置仍可能在 Linux 运行时落回 `cmd.exe /c codex.cmd`，必须一并修正为显式合同或可解释的 fail-fast 行为。

## BDD Scenarios

- `BDD: 维护仓发布链路必须携带 DCC Codex 运行时合同 -> Given 使用维护仓构建测试服 backend 运行时 / When 生成 .env 与 docker-compose.yml / Then 其中必须包含 DCC 项目编码识别所需的 Codex 命令、CODEX_HOME 和挂载路径。`
- `BDD: backend 容器缺少 Codex 运行时时不得误判跑通 -> Given backend 容器里没有可执行 Codex 命令或认证目录 / When 文控触发内容级识别 / Then 系统必须返回明确失败，而不能以健康检查通过或文件名直连样本替代成功结论。`
- `BDD: 文件名不足时内容识别能真实回写 -> Given 真实文件名不包含唯一明确项目编码 / When 文控在测试服触发识别 / Then 后端必须读取文件内容并由 Codex 返回有效候选，再把项目编码和项目名称回写到受控文件。`

## Acceptance Criteria

- 维护仓新增的合同测试先失败后通过，覆盖 DCC Codex 运行时变量和挂载。
- 测试服 backend 容器内可执行配置路径上的 Codex CLI，并能读取 `backend-codex-home`。
- 真实内容识别样本通过前端路径触发成功，最终 API 与数据库都能回读到正确项目编码和项目名称。
- 全程不在仓库、任务文档或最终答复中泄露任何认证内容。

## Open Questions

- 测试服最终使用哪一个真实 `controlledFileId` 作为“文件名不足、只能靠内容识别”的验收样本。
- `backend-codex-home` 的正式来源是复用宿主机 `/root/.codex`，还是转为独立的服务级运行时目录。
- 若维护仓修复后 backend 共享配置仍默认 Windows 命令，是否同步在业务后端仓补一个 Linux 运行时 fail-fast 或显式默认修正。
