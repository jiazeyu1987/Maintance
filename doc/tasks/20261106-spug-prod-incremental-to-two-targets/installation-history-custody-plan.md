# Installation receipt history verification

## Current Status
completed

## Goal
Keep every original history byte protected while correctly auditing the explicitly authorized control upgrades. The original inventory includes root/target-installation.json, an active receipt replaced by each authorized installation. Its original bytes must be verified at the installer's immutable archived previousReceiptPin, and every subsequent activation must form a complete byte-exact chain to the selected current receipt. Do not rewrite the original inventory or claim that the active receipt's original path stayed unchanged.

## Milestones and verification
1. Identify the exact installation reports and original active-receipt pin for58/59.
2. RED: the existing unchanged-path verifier must expose the authorized active-receipt change on the actual server; retain the original error.
3. Verify every archived receipt and its owner/control pins, original target/source definitions, adjacent generation byte equality and selected live receipt. Reject missing, tampered or reordered links using the same actual read-only evidence.
4. Update only task-local independent verifiers: all other original paths remain byte-exact; report the immutable path count separately from the one authorized active receipt. Both native acceptance and final closeout must require this custody proof. No production/runtime changes, new restore or new build.

## Verification result
All four milestones completed. Actual RED is history-receipt-custody-red.json, with its original error retained privately. Actual positive and five negative read-only cases passed separately on58/59 in history-receipt-custody-green-58/59.json. Full original metadata preflights passed:58 has1991 original files,1990 unchanged immutable paths and one archived original active receipt through five authorized generations;59 has1760 originals,1759 immutable paths and two generations. Original byte totals remain11035996/10947375. Original inventories were not changed. Native acceptance and final closeout now require the same custody proof. Final post-restore metadata checks remain required by the parent task; this plan's completion does not declare either restore accepted. UTF-8/syntax/private-value verification passed with74 known private values and zero findings.

## BDD
Given the frozen original history inventory and authorized control installations, when auditing history, then every immutable original path matches and the one active receipt's original bytes plus every later generation are preserved through a complete archived-to-active chain.

Given a missing, tampered or reordered chain link, when auditing the same real retained receipts, then verification fails. No generic path exception, deletion, baseline rewrite or substituted successful history is permitted.

## 经验门禁
- Trigger: authorized control upgrades replace the one active installation receipt while prior operation history must stay immutable.
- Preflight check: exact root, source/target, installation report sequence, previous/current pin identities and selected active installation.
- Blocker: any missing receipt, pin mismatch, chain gap, changed source/target definitions, unrelated changed original file or unknown activation.
- Verification: actual full original metadata read; all archived receipt bytes and pinned owner/control documents; exact adjacent byte identities; selected current live receipt and configuration pins; negative rejection on actual retained inputs.
- Forbidden action: do not remove the active receipt from protection without custody proof, rewrite old inventories or report original path preservation for an authorized changed path.
- Evidence: execution-log.md, original inventory, installation reports, RED and independent custody verification records. Private raw errors remain outside Git.

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。An explicit, byte-exact authorized receipt chain replaces the incorrect unchanged-path assumption for exactly one known active receipt; all other original paths retain their original check.
- 是否从根因和长期维护角度解决：是。Separate immutable historical documents from an explicitly versioned active control receipt and prove both lifecycles.
- 是否存在临时补丁或绕过：否。No production change or server mutation.
