package com.intruoyi.maintenance.runtime;

public record ReleaseOperationLockOwner(
        String executorHost,
        String executorPid,
        String executorIdentity,
        String leaseToken
) {
}
