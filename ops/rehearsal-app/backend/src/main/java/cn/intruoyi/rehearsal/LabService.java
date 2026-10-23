package cn.intruoyi.rehearsal;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import io.minio.*;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.*;
import java.util.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;
import static org.springframework.http.HttpStatus.*;

@Service
public class LabService implements ApplicationRunner {
    final EntryMapper entries;
    final JdbcTemplate db;
    final StringRedisTemplate redis;
    final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    final MinioClient minio;
    final String initialPassword;
    final String secondaryPassword;
    static final String BUCKET="rehearsal-122";
    public record Actor(long tenantId, String username, String tenantName) {}
    static Actor actor(long tenantId) {
        if(tenantId==122)return new Actor(122,"aoteman","测试租户");
        if(tenantId==123)return new Actor(123,"recovery_tenant123","隔离演练租户");
        throw new ResponseStatusException(UNAUTHORIZED,"租户无效");
    }
    public LabService(EntryMapper entries, JdbcTemplate db, StringRedisTemplate redis,
                      @Value("${MINIO_ROOT_USER}") String key, @Value("${MINIO_ROOT_PASSWORD}") String secret,
                      @Value("${LAB_PASSWORD}") String password,
                      @Value("${LAB_SECONDARY_PASSWORD}") String secondPassword) {
        this.entries=entries; this.db=db; this.redis=redis; initialPassword=password; secondaryPassword=secondPassword;
        minio=MinioClient.builder().endpoint("http://minio:9000").credentials(key,secret).build();
    }
    public void run(ApplicationArguments args) throws Exception {
        // A fresh dedicated schema is the only supported installation target.
        db.queryForList("SHOW TABLES");
        db.execute("CREATE TABLE IF NOT EXISTS lab_user (id BIGINT PRIMARY KEY, tenant_id BIGINT NOT NULL, username VARCHAR(64) NOT NULL UNIQUE, password_hash VARCHAR(100) NOT NULL)");
        db.execute("CREATE TABLE IF NOT EXISTS lab_record (id BIGINT PRIMARY KEY AUTO_INCREMENT, tenant_id BIGINT NOT NULL, title VARCHAR(120) NOT NULL, content TEXT NOT NULL, created_at DATETIME(6) NOT NULL, updated_at DATETIME(6) NOT NULL, INDEX(tenant_id))");
        db.execute("CREATE TABLE IF NOT EXISTS lab_attachment (id CHAR(36) PRIMARY KEY, tenant_id BIGINT NOT NULL, record_id BIGINT NOT NULL, name VARCHAR(255) NOT NULL, object_key VARCHAR(255) NOT NULL, size BIGINT NOT NULL, sha256 CHAR(64) NOT NULL, FOREIGN KEY(record_id) REFERENCES lab_record(id))");
        for(String table:List.of("lab_user","lab_record","lab_attachment")) db.queryForList("DESCRIBE "+table);
        if(db.queryForObject("SELECT COUNT(*) FROM lab_user",Long.class)==0) {
            if(initialPassword.length()<16||secondaryPassword.length()<16||initialPassword.equals(secondaryPassword)) throw new IllegalStateException("LAB_DISTINCT_PASSWORDS_REQUIRED");
            db.update("INSERT INTO lab_user VALUES(122,122,'aoteman',?)",encoder.encode(initialPassword));
            db.update("INSERT INTO lab_user VALUES(123,123,'recovery_tenant123',?)",encoder.encode(secondaryPassword));
        }
        for(long tenantId:List.of(122L,123L)) {
            Actor expected=actor(tenantId);
            if(db.queryForObject("SELECT COUNT(*) FROM lab_user WHERE tenant_id=? AND username=?",Long.class,tenantId,expected.username())!=1)
                throw new IllegalStateException("LAB_TENANT_ACCOUNT_MISSING");
        }
        redis.getConnectionFactory().getConnection().ping();
        if(!minio.bucketExists(BucketExistsArgs.builder().bucket(BUCKET).build())) minio.makeBucket(MakeBucketArgs.builder().bucket(BUCKET).build());
    }
    public String login(long tenantId,String username,String password) {
        Actor identity=actor(tenantId);
        String attemptsKey="login-attempts:"+tenantId;
        Long attempts=redis.opsForValue().increment(attemptsKey);
        if(attempts==1)redis.expire(attemptsKey,Duration.ofMinutes(1));
        if(attempts>30)throw new ResponseStatusException(TOO_MANY_REQUESTS,"登录频繁，请稍后重试");
        var hashes=db.queryForList("SELECT password_hash FROM lab_user WHERE username=? AND tenant_id=?",String.class,username,tenantId);
        if(!identity.username().equals(username)||hashes.size()!=1||!encoder.matches(password,hashes.get(0)))throw new ResponseStatusException(UNAUTHORIZED,"账号或密码错误");
        String token=UUID.randomUUID().toString()+UUID.randomUUID();
        redis.opsForValue().set("session:"+token,tenantId+":"+username,Duration.ofHours(8)); return token;
    }
    public Actor authenticate(String token) {
        if(token==null||token.isBlank()||token.length()>100)throw new ResponseStatusException(UNAUTHORIZED,"请登录演练租户");
        String session=redis.opsForValue().get("session:"+token);
        for(long tenantId:List.of(122L,123L)) {
            Actor identity=actor(tenantId);
            if((tenantId+":"+identity.username()).equals(session))return identity;
        }
        throw new ResponseStatusException(UNAUTHORIZED,"登录会话无效");
    }
    public void logout(String token) { redis.delete("session:"+token); }
    public List<Entry> list(Actor actor){return entries.selectList(new QueryWrapper<Entry>().eq("tenant_id",actor.tenantId()).orderByDesc("id").last("LIMIT 200"));}
    public Entry get(Actor actor,long id){Entry e=entries.selectOne(new QueryWrapper<Entry>().eq("id",id).eq("tenant_id",actor.tenantId()));if(e==null)throw new ResponseStatusException(NOT_FOUND,"记录不存在");return e;}
    @Transactional public Entry save(Actor actor,Long id,String title,String content){
        Entry e=id==null?new Entry():get(actor,id);e.tenantId=actor.tenantId();e.title=title;e.content=content;e.updatedAt=LocalDateTime.now();
        if(id==null){e.createdAt=e.updatedAt;entries.insert(e);}else entries.update(e,new QueryWrapper<Entry>().eq("id",id).eq("tenant_id",actor.tenantId()));return e;
    }
    @Transactional public void delete(Actor actor,long id){get(actor,id);if(!attachments(actor,id).isEmpty())throw new ResponseStatusException(CONFLICT,"请先删除附件");entries.delete(new QueryWrapper<Entry>().eq("id",id).eq("tenant_id",actor.tenantId()));}
    public List<Map<String,Object>> attachments(Actor actor,long id){get(actor,id);return db.queryForList("SELECT id,name,size,sha256 FROM lab_attachment WHERE record_id=? AND tenant_id=?",id,actor.tenantId());}
    public Map<String,Object> upload(Actor actor,long id,String name,byte[] bytes) throws Exception {
        get(actor,id);if(name==null||name.isBlank()||name.length()>200||name.contains("/")||name.contains("\\"))throw new ResponseStatusException(BAD_REQUEST,"附件名称无效");
        String uuid=UUID.randomUUID().toString(),key="tenant"+actor.tenantId()+"/"+id+"/"+uuid;
        String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        minio.putObject(PutObjectArgs.builder().bucket(BUCKET).object(key).stream(new ByteArrayInputStream(bytes),bytes.length,-1).contentType("application/octet-stream").build());
        // No successful response unless both object storage and metadata are committed.
        db.update("INSERT INTO lab_attachment VALUES(?,?,?,?,?,?,?)",uuid,actor.tenantId(),id,name,key,bytes.length,sha);
        return Map.of("id",uuid,"sha256",sha);
    }
    public Map<String,Object> attachment(Actor actor,String id){var rows=db.queryForList("SELECT * FROM lab_attachment WHERE id=? AND tenant_id=?",id,actor.tenantId());if(rows.size()!=1)throw new ResponseStatusException(NOT_FOUND,"附件不存在");return rows.get(0);}
    public byte[] download(Actor actor,String id) throws Exception {
        var a=attachment(actor,id);try(var stream=minio.getObject(GetObjectArgs.builder().bucket(BUCKET).object((String)a.get("object_key")).build())) {
            byte[] bytes=stream.readAllBytes();String sha=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
            if(!sha.equals(a.get("sha256")))throw new IllegalStateException("ATTACHMENT_HASH_MISMATCH");return bytes;
        }
    }
    public void deleteAttachment(Actor actor,String id) throws Exception {var a=attachment(actor,id);minio.removeObject(RemoveObjectArgs.builder().bucket(BUCKET).object((String)a.get("object_key")).build());db.update("DELETE FROM lab_attachment WHERE id=? AND tenant_id=?",id,actor.tenantId());}
}
