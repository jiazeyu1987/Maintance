package cn.intruoyi.rehearsal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import java.util.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

class TenantIsolationTest {
    EntryMapper entries;
    JdbcTemplate db;
    StringRedisTemplate redis;
    ValueOperations<String,String> values;
    LabService service;

    @BeforeEach @SuppressWarnings("unchecked") void setup() {
        entries=mock(EntryMapper.class); db=mock(JdbcTemplate.class);
        redis=mock(StringRedisTemplate.class); values=mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(values);
        service=new LabService(entries,db,redis,"lab-key","lab-secret","primary-long-password","secondary-long-password");
    }

    @Test void identityComesFromExactSessionAccountAndTenant() {
        when(values.get("session:one")).thenReturn("122:aoteman");
        when(values.get("session:two")).thenReturn("123:recovery_tenant123");
        assertEquals(122,service.authenticate("one").tenantId());
        assertEquals("recovery_tenant123",service.authenticate("two").username());
        for(String invalid:List.of("122", "123:aoteman", "122:recovery_tenant123", "124:other")) {
            when(values.get("session:invalid")).thenReturn(invalid);
            assertEquals(401,assertThrows(ResponseStatusException.class,()->service.authenticate("invalid")).getStatusCode().value());
        }
        assertThrows(ResponseStatusException.class,()->service.authenticate(null));
        assertThrows(ResponseStatusException.class,()->service.authenticate("missing"));
    }

    @Test void anotherTenantsRecordCannotBeReadChangedDeletedOrUsedForUpload() {
        LabService.Actor actor=LabService.actor(123);
        when(entries.selectOne(any(Wrapper.class))).thenAnswer(call->{
            Wrapper<?> query=call.getArgument(0);
            String sql=query.getSqlSegment();
            assertTrue(sql.contains("tenant_id") && sql.contains("id"));
            return null;
        });
        assertNotFound(()->service.get(actor,1));
        assertNotFound(()->service.save(actor,1L,"changed","changed"));
        assertNotFound(()->service.delete(actor,1));
        assertNotFound(()->service.attachments(actor,1));
        assertNotFound(()->service.upload(actor,1,"x.txt",new byte[]{1}));
        verify(entries,never()).update(any(Entry.class),any(Wrapper.class));
        verify(entries,never()).delete(any(Wrapper.class));
        verifyNoInteractions(db);
    }

    @Test void anotherTenantsAttachmentCannotBeReadDownloadedOrDeleted() {
        LabService.Actor actor=LabService.actor(123);
        when(db.queryForList("SELECT * FROM lab_attachment WHERE id=? AND tenant_id=?","foreign",123L)).thenReturn(List.of());
        assertNotFound(()->service.attachment(actor,"foreign"));
        assertNotFound(()->service.download(actor,"foreign"));
        assertNotFound(()->service.deleteAttachment(actor,"foreign"));
        verify(db,never()).update(anyString(),any(Object[].class));
    }

    @Test void loginDoesNotAcceptAnotherTenantsAccountOrPassword() {
        when(values.increment(anyString())).thenReturn(1L);
        when(db.queryForList(anyString(),eq(String.class),eq("aoteman"),eq(123L)))
            .thenReturn(List.of(service.encoder.encode("primary-long-password")));
        assertEquals(401,assertThrows(ResponseStatusException.class,
            ()->service.login(123,"aoteman","primary-long-password")).getStatusCode().value());
        assertThrows(ResponseStatusException.class,()->service.login(124,"aoteman","primary-long-password"));
        verify(values,never()).set(startsWith("session:"),anyString(),any(java.time.Duration.class));
    }

    @Test void newRecordAlwaysBelongsToTheAuthenticatedTenant() {
        Entry saved=service.save(LabService.actor(123),null,"same title","tenant 123");
        assertEquals(123L,saved.tenantId);
        verify(entries).insert(saved);
    }

    interface CheckedAction {void run() throws Exception;}
    static void assertNotFound(CheckedAction action) {
        assertEquals(404,assertThrows(ResponseStatusException.class,action::run).getStatusCode().value());
    }
}
