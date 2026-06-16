package com.intruoyi.maintenance.runtime;

import java.util.List;

public record RuntimeControlCommand(
        String environment,
        String component,
        String scriptPath,
        List<String> arguments
) {
}
