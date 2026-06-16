package com.intruoyi.maintenance.runtime;

public record ApiResult<T>(Integer code, T data, String msg) {

    public static <T> ApiResult<T> success(T data) {
        return new ApiResult<>(0, data, "");
    }

    public static <T> ApiResult<T> error(int code, String message) {
        return new ApiResult<>(code, null, message);
    }
}
