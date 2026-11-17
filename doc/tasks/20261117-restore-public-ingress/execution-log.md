BDD: Given恢复容器处于internal网络，When安装公开入口，Then仅172.30.30.59:8081可达前端，目标地址由准备配置subnet和角色顺序推导，后续重建同配置无需改入口。
RED: python -m unittest test_prepare_target_ingress -> ModuleNotFoundError，未实现生成器。
GREEN: 同命令 -> 3 tests PASS；主机/单端口绑定、配置地址变化、非法输入显式失败通过。
设计：systemd socket/proxyd及精确firewalld规则为正式持久配置，不安装组件、不改恢复容器，不开放数据库/后端端口。原生准备配置网络或服务顺序变更时重新运行该安装器；同配置重建无需改动。
安装：python prepare_target_ingress.py --config /mnt/intruoyi-data/recovery-tools/prepare-target.private.json --port 8081 --apply。默认无--apply仅生成计划。回退：停用spug-recovery-frontend.socket/service并移除相同精确rich rule，不改其他规则或数据。
GREEN: experience-preflight -> PASS。已核现有proxy/systemd219、前端内部200、实际固定IP和防火墙；安装只写两个独立unit及指定8081规则。保留5容器ID，使用已有登录凭据走真实公开地址。原源代码与配置不变，未修改NAS或业务数据库。
