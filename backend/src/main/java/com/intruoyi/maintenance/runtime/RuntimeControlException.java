package com.intruoyi.maintenance.runtime;

public class RuntimeControlException extends RuntimeException {

    public RuntimeControlException(String message) {
        super(message);
    }

    public RuntimeControlException(String message, Throwable cause) {
        super(message, cause);
    }
}
