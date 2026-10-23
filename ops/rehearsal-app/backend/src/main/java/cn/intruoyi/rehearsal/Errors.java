package cn.intruoyi.rehearsal;
import java.util.Map;
import org.slf4j.*;
import org.springframework.http.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.server.ResponseStatusException;
@RestControllerAdvice
public class Errors {
    private static final Logger log=LoggerFactory.getLogger(Errors.class);
    @ExceptionHandler(ResponseStatusException.class) ResponseEntity<?> expected(ResponseStatusException e){return ResponseEntity.status(e.getStatusCode()).body(Map.of("message",e.getReason()));}
    @ExceptionHandler({MethodArgumentNotValidException.class,MaxUploadSizeExceededException.class}) ResponseEntity<?> invalid(Exception e){return ResponseEntity.badRequest().body(Map.of("message","输入无效，请检查字段长度或附件大小"));}
    @ExceptionHandler(Exception.class) ResponseEntity<?> failure(Exception e){log.error("Request failed: {}",e.getClass().getSimpleName());return ResponseEntity.internalServerError().body(Map.of("message","操作失败，请检查服务日志及存储状态"));}
}
