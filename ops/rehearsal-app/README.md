# 最小备份演练应用

与 IntRuoyi 使用相同主要技术栈：Vue 3 / TypeScript / Vite / Element Plus，Java / Spring Boot / MyBatis-Plus，MySQL / Redis / MinIO。包含登录、测试租户 122/aoteman、隔离演练租户 123/recovery_tenant123、记录 CRUD 和附件读写；不加载 ERP、MES、BPM 等业务模块。第二租户限明确授权的新独立演练实例使用。

登录时显式选择租户，后端使用 Redis 会话中的租户及账号识别身份，所有记录与附件接口校验归属，附件对象键按 tenant122/tenant123 分隔。两个账号密码独立，从 LAB_PASSWORD/LAB_SECONDARY_PASSWORD 注入；只在全新 schema 初始化，缺少任一账号即失败，不对旧单租户实例自动补租户。恢复时沿用归档账号与密码摘要，不根据目标环境重置账号。

三服使用同一镜像包，应用入口为各服务器 `:38082`。数据库、缓存、附件仅通过独立内部 Docker 网络连接，不发布基础组件端口；数据目录和容器不复用现有 IntRuoyi。MySQL 开启 ROW binlog，Redis 开启 AOF。每服内存上限合计约 1.6 GiB，实际占用在验收后记录。

`build_release.py --output <本机输出目录>` 要求干净的专用工作树，完成 Maven/Vite 构建、生成并从前端镜像读回 release-info.json、导出带 SHA-256 的镜像包。

在各服务器校验包摘要并 docker load 后运行 `deploy.py --root <全新数据盘目录> --host <服务器地址> --manifest <manifest.json>`。安装器遇到同名实例或目录即停止；不覆盖、不删除任何已有环境。登录凭据保存在实例目录的 `login.private.json`，权限 0600，不进入版本库。首次初始化只建立 schema 和测试账号，业务数据必须通过页面创建。

发布顺序：build-release → publish-test → mark-tested → promote-prod → promote-backup。应用部署和页面验证不等同于 Spug 备份源已登记，也不等同于完成全量、增量和恢复演练；新实例需使用新的源、目标身份接入，不能沿用已删除旧实例的配置。

附件先写对象、再写元数据；元数据失败会明确报错，可能留下未引用对象。删除时先删除对象再删除元数据，失败保留原记录供定位。不要把跨存储的两步操作声称为分布式原子事务。上限 200 条展示、单附件 5 MiB，适合小数据演练，不用于生产业务。
