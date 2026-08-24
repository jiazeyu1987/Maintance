# r11 正式服晋级验证报告

## 结论

阻塞，不能判定正式服发布成功。测试通过标记和正式服预览成功；正式服实际晋级 operation 因迁移 scope dependency 阻塞并已 fail-fast，正式服已恢复发布前运行态。

## 证据

- ReleaseTag：`release-20260823-intmain-training-r260823f-r11`
- mark-tested：`op-2026-08-24T161343310401700Z-81371129-617a-45cf-a42c-c720d8c5b0bd`，SUCCESS。
- prod preview：`release-20260823-intmain-training-r260823f-r11-preflight-release-dry-run.json`，status=passed，target=prod/172.30.30.57，无远程写入。
- promote-prod：`op-2026-08-24T162302044432900Z-4eca53c5-366b-4699-b2a7-5a9876992d65`，FAILED；原因是正式库 `preflight-plan.json` status=blocked，包含 `BLOCKED_SCOPE_DEPENDENCY`。
- 恢复后正式服只读检查：`.env IMAGE_TAG=release-20260716-intmain-codeonly-three-env-r260716d-r1`；backend 实际镜像仍为旧 tag、health HTTP 200 且 body `status=UP`；frontend HTTP 200；prod release lock status=FAILED；运行控制台 `prodCurrentReleaseTag=null`。
- 未执行 `promote-backup`，未访问备份服。

## 放行条件

先由发布负责人补齐正式库缺失迁移依赖或重新构建包含完整依赖链的合规发布包，再以同一 releaseTag 完成新的 prod preview 与 promote-prod；禁止手工改迁移状态、tested 标记或跳过 `BLOCKED_SCOPE_DEPENDENCY`。
