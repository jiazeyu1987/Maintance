## 20261126-prod-backend-auto-restart-check

- 用户需求：现在的正式服后端如果挂了会自动重启吗。
- 命令意图：通过受保护SSH配置只读docker inspect、systemctl show/list及health GET，核异常退出与健康失败两类恢复；不重启或写入服务器。
- 验证结果：正式后端unless-stopped，异常退出自动拉起；当前UP、restartCount0。Docker healthcheck未配置，独立service-recovery未安装/启用，因此假死/健康失败尚无该自动恢复能力。
- 探针首轮Python3.6参数不兼容已保留，改PIPE后同范围核查PASS；证据见doc/tasks/20261126-prod-backend-auto-restart-check/verification.md和runtime-readonly-evidence.json。
