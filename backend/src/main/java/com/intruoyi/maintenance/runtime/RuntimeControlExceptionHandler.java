package com.intruoyi.maintenance.runtime;

import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class RuntimeControlExceptionHandler {

    @ExceptionHandler(RuntimeControlException.class)
    public ApiResult<Void> handleRuntimeControl(RuntimeControlException ex) {
        return ApiResult.error(400, ex.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResult<Void> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .findFirst()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .orElse("request validation failed");
        return ApiResult.error(400, message);
    }
}
