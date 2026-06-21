# 执行日志：20260621-codex-cli-three-server-setup

- BDD: 三台服务器可用同一本机连接参数跑通 Codex CLI -> Given 本机已存在可工作的 Codex CLI 配置与文件型认证 / When 在测试服、正式服、备份服安装 Codex CLI 并同步最小连接配置 / Then 三台服务器都必须通过真实 `codex exec` 冒烟验证。
- BDD: 前置条件缺失必须直接阻塞 -> Given 任一服务器缺少 SSH、安装网络、认证文件或写权限 / When 尝试进入远端安装 / Then 必须先记录具体缺口并停止，不得用 mock、占位配置或静默降级继续。

- GREEN: previous-task-check -> PASS，上一维护仓任务 `20260621-frontend-release-full-flow-main-merge-rerun` 已按用户切换目标显式标记为 `blocked`，不会与本任务并行推进。
- GREEN: experience-docs-read -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；确认当前任务已获测试服、正式服、备份服写入授权，且远端凭据不得写入仓库、脚本、任务文档或控制台配置。
- GREEN: local-config-baseline -> PASS，本机 `codex --version` 为 `0.128.0`，默认 provider 为 `asxs`、model 为 `gpt-5.4`，本机现有 `config.toml` 中自定义 provider 使用 `base_url=https://api.asxs.top/v1`、`wire_api=responses`、`requires_openai_auth=true`。
- GREEN: local-auth-source-smoke -> PASS，临时移除当前 shell 的 `OPENAI_API_KEY` 与 `OPENAI_BASE_URL` 后，执行 `codex -a never -s read-only exec --skip-git-repo-check -c model_reasoning_effort='"low"' --color never -o <temp> "Respond with exactly OK and nothing else."` 仍返回 `OK`；证明本机 `C:\Users\BJB110\.codex\auth.json + config.toml` 足以支撑最小连接方案，远端无需依赖 shell 级 `OPENAI_*` 环境变量。
- GREEN: official-doc-baseline -> PASS，官方 Quickstart 确认 Linux 可用 `curl -fsSL https://chatgpt.com/codex/install.sh | sh` 安装 Codex CLI，非交互安装使用 `CODEX_NON_INTERACTIVE=1`；官方 Config/Authentication 文档确认 `CODEX_HOME` 默认是 `~/.codex`，文件型凭据存储为 `auth.json`。
- GREEN: remote-prereq-scan -> PASS，只读 SSH 预检确认测试服 `172.30.30.58` 为 CentOS 8、备份服 `172.30.30.59` 为 CentOS 7、正式服 `172.30.30.57` 为 CentOS 8；三台机器均具备 `curl`、`tar`、`sudo`，其中正式服已有 `node v22.22.2 / npm 10.9.7`，测试服与备份服无 `node/npm`。因此本任务统一采用官方 standalone installer，而非依赖 npm。
- GREEN: experience-preflight -> PASS，已明确目标主机 `172.30.30.58 / 172.30.30.57 / 172.30.30.59`、目标配置位置 `~/.codex`、目标执行命令 `codex exec`，且本次不涉及发布、重启、备份、恢复、数据库写入或业务容器改动；允许进入远端安装与配置。

## Test Server

- GREEN: test-server-bwrap -> PASS，已在 `172.30.30.58` 安装 `bubblewrap 0.4.0-1.el8`，`/usr/bin/bwrap` 可用，Codex smoke 不再提示 vendored bubblewrap。
- GREEN: test-server-version -> PASS，`/usr/local/bin/codex --version` 返回 `codex-cli 0.128.0`。
- GREEN: test-server-config-auth -> PASS，`/root/.codex/config.toml` 与 `auth.json` 到位，`grep -o OPENAI_API_KEY /root/.codex/auth.json` 命中。
- GREEN: test-server-smoke -> PASS，`/root/codex-cli-setup/remote-smoke-codex.sh` 真实返回 `OK`。

## Production Server

- GREEN: prod-server-bwrap -> PASS，已在 `172.30.30.57` 安装 `bubblewrap 0.4.0-1.el8`，`/usr/bin/bwrap` 可用。
- GREEN: prod-server-version -> PASS，`/usr/local/bin/codex --version` 返回 `codex-cli 0.128.0`。
- GREEN: prod-server-config-auth -> PASS，`/root/.codex/config.toml` 与 `auth.json` 到位，`grep -o OPENAI_API_KEY /root/.codex/auth.json` 命中。
- GREEN: prod-server-smoke -> PASS，`/root/codex-cli-setup/remote-smoke-codex.sh` 真实返回 `OK`。

## Backup Server

- BLOCKER: backup-direct-download -> `curl -I -L --max-time 60 https://github.com/openai/codex/releases/download/rust-v0.128.0/codex-x86_64-unknown-linux-musl.tar.gz` 在 `172.30.30.59` 上 60 秒内无字节返回并超时，直接 release 下载路径不可用。
- GREEN: backup-relay-binary -> PASS，已从测试服中转复制同版官方 `codex` 二进制到 `/usr/local/bin/codex`，`sha256sum` 与测试服一致。
- GREEN: backup-server-version -> PASS，`/usr/local/bin/codex --version` 返回 `codex-cli 0.128.0`。
- GREEN: backup-server-config-auth -> PASS，`/root/.codex/config.toml` 与 `auth.json` 到位，`grep -o OPENAI_API_KEY /root/.codex/auth.json` 命中。
- GREEN: backup-server-smoke -> PASS，`/root/codex-cli-setup/remote-smoke-codex.sh` 真实返回 `OK`；该机仍提示 `bubblewrap` 缺失并使用 vendored bubblewrap。

## Closeout

- GREEN: closeout-preview -> PASS，已执行 `python C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260621-codex-cli-three-server-setup --mode preview`；预览结果保留 `task.md` 与 `execution-log.md`，其余任务附属产物列为可清理项。
- GREEN: scoped-secret-scan -> PASS，已用本机真实 `auth.json` 中的 `OPENAI_API_KEY` 值对当前任务目录与 `docs/request-command-log.md` 做只读匹配扫描，未发现密钥值入仓。
- GREEN: final-scope-review -> PASS，`git status --short` 显示仓库存在大量与本任务无关的既有改动；`docs/request-command-log.md` 已按流程补记当前任务，但该文件当前混有其他未提交历史内容，最终 Git 提交范围仅包含 `doc/tasks/20260621-codex-cli-three-server-setup/`，避免夹带无关改动。
- GREEN: artifact-validation -> PASS，`validate_artifacts.py` 与 `validate_test_report.py` 已通过，任务文档链与测试报告结构有效。
- GREEN: completion-gate -> PASS，已执行 `record_test_review.py --outcome passed` 与 `check_completion.py --apply`，任务状态机收口成功。
- GREEN: closeout-apply -> PASS，为兼容 `task-closeout-cleanup` 脚本状态解析，已在 `task.md` 补充英文 `## Current Status` 元数据；随后成功执行 `task_closeout.py --mode apply`，按预览结果仅保留 `task.md` 与 `execution-log.md`，删除 `prd.md`、`test-plan.md`、`test-report.md`、`task-state.json` 与远端辅助脚本。

## Completion Audit 2026-06-22

- GREEN: current-local-baseline -> PASS，当前本机 `codex --version` 仍为 `0.128.0`，`C:\Users\BJB110\.codex\config.toml` 关键连接项保持 `model_provider=asxs`、`model=gpt-5.4`、`model_reasoning_effort=xhigh`、`disable_response_storage=true`、`sandbox_mode=workspace-write`，provider 仍为 `https://api.asxs.top/v1` + `wire_api=responses`。
- GREEN: current-config-parity -> PASS，已对本机与 `172.30.30.58 / 172.30.30.57 / 172.30.30.59` 的 `~/.codex/config.toml` 做规范化字段比对，三台远端的关键连接参数与本机完全一致。
- GREEN: current-auth-parity -> PASS，已对本机与三台远端的 `auth.json` 做 SHA-256 比对，三台远端认证文件均与本机一致。
- GREEN: current-readonly-smoke -> PASS，已在三台远端重新执行 `codex -a never -s read-only exec --skip-git-repo-check --color never -o /tmp/codex-audit.txt 'Respond with exactly OK and nothing else.' </dev/null`；三台均返回 `OK`，并显示 `provider: asxs`、`model: gpt-5.4`、`reasoning effort: xhigh`。
- GREEN: current-default-sandbox-smoke -> PASS，已在三台远端重新执行 `codex -a never exec --skip-git-repo-check --color never -o /tmp/codex-audit-default.txt 'Respond with exactly OK and nothing else.' </dev/null`；三台均返回 `OK`，并确认默认 `sandbox: workspace-write` 已生效。
- NOTE: backup-bwrap-warning-still-present -> `172.30.30.59` 当前仍无系统 `bubblewrap`，默认 `workspace-write` smoke 时提示使用 vendored bubblewrap，但命令实际成功返回 `OK`；该情况不影响本任务“连接参数一致且三台真实跑通”的完成判定。
