BDD: Given恢复容器处于internal网络，When安装公开入口，Then仅172.30.30.59:8081可达前端，目标地址由准备配置subnet和角色顺序推导，后续重建同配置无需改入口。
RED: python -m unittest test_prepare_target_ingress -> ModuleNotFoundError，未实现生成器。
GREEN: 同命令 -> 3 tests PASS；主机/单端口绑定、配置地址变化、非法输入显式失败通过。
设计：systemd socket/proxyd及精确firewalld规则为正式持久配置，不安装组件、不改恢复容器，不开放数据库/后端端口。原生准备配置网络或服务顺序变更时重新运行该安装器；同配置重建无需改动。
安装：python prepare_target_ingress.py --config /mnt/intruoyi-data/recovery-tools/prepare-target.private.json --port 8081 --apply。默认无--apply仅生成计划。回退：停用spug-recovery-frontend.socket/service并移除相同精确rich rule，不改其他规则或数据。
GREEN: experience-preflight -> PASS。已核现有proxy/systemd219、前端内部200、实际固定IP和防火墙；安装只写两个独立unit及指定8081规则。保留5容器ID，使用已有登录凭据走真实公开地址。原源代码与配置不变，未修改NAS或业务数据库。

现场首装：内部网络对应HostConfig的127.0.0.1:18089绑定未形成宿主监听；安装公开入口后/index HTTP200。systemd219 verify暴露network-online与sockets.target启动环；RED新增FreeBind/无network-online断言失败，修正为FreeBind=true后3测试PASS。最终提交f33673f安装，unitVerify exit0/stderr空；精确规则重复添加仅ALREADY_ENABLED提示。
GREEN: 真实Playwright通过http://172.30.30.59:8081登录并进入用户管理，20可见行/共2117，版本18-57-58，业务修改0。证据sixstep-20261116/acceptance/target-59-public-incremental-business.private.json。5容器ID未变，未重新恢复。
GREEN: experience-preflight -> PASS。实现已提交246a1ca/f33673f，只合并本任务新增入口脚本、测试和子任务记录；父任务dirty保持，随后主线定向验证和精确worktree清理。

CLOSEOUT PASS: f33673f已融合int_main，主线3测试PASS；独立实现worktree已删除，代码和完整记录均在主线。公开入口已持久配置，未保留临时隧道。未执行服务器重启，开机配置仅经systemd-analyze及enable验证，不声称真实重启验收。
