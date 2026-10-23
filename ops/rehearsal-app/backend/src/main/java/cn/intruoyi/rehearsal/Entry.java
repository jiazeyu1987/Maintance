package cn.intruoyi.rehearsal;

import com.baomidou.mybatisplus.annotation.*;
import java.time.LocalDateTime;

@TableName("lab_record")
public class Entry {
    @TableId(type=IdType.AUTO) public Long id;
    public Long tenantId;
    public String title;
    public String content;
    public LocalDateTime createdAt;
    public LocalDateTime updatedAt;
}
