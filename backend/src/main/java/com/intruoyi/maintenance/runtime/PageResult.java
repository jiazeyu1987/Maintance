package com.intruoyi.maintenance.runtime;

import java.util.List;

public record PageResult<T>(List<T> list, long total) {

    public static <T> PageResult<T> of(List<T> list) {
        return new PageResult<>(list, list.size());
    }
}
