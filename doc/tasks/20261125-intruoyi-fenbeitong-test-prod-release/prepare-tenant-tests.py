"""Install the regression scenarios before changing production code."""
from pathlib import Path
import subprocess
root=Path('C:/SpugHandoff/release/fenbeitong-ticket-tenant-20261126')
assert subprocess.check_output(['git','-C',str(root),'status','--porcelain']).strip()==b''
p=root/'IntRuoyiBackend/yudao-module-system/src/test/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthControllerTest.java'
s=p.read_text(encoding='utf-8')
s=s.replace('import org.junit.jupiter.params.provider.ValueSource;', 'import org.junit.jupiter.params.provider.ValueSource;\nimport org.junit.jupiter.params.provider.NullSource;')
s=s.replace('void createFenbeitongAssistantTicketStoresPermissionsWhenUserCanQuery() {', 'void createFenbeitongAssistantTicketStoresPermissionsWhenUserCanQuery() {\n        TenantContextHolder.setTenantId(169L);')
s=s.replace('assertTrue(keyCaptor.getValue().startsWith("fenbeitong_assistant_ticket:"));', 'assertTrue(keyCaptor.getValue().startsWith("fenbeitong_assistant_ticket:"));\n            assertTrue(valueCaptor.getValue().contains("\\\"tenantId\\\":169"));')
prefix,suffix=s.split('void validateFenbeitongAssistantTicketReturnsPermissionsAndKingdeeConfig()',1)
suffix=suffix.replace(r'{\"userId\":303,\"permissions\":',r'{\"userId\":303,\"tenantId\":169,\"permissions\":')
s=prefix+'void validateFenbeitongAssistantTicketReturnsPermissionsAndKingdeeConfig()'+suffix
marker='    @Test\n    void getAndStartFenbeitongAssistantReturnServiceStatus()'
assert marker in s
new='''    @ParameterizedTest
    @NullSource
    @ValueSource(longs = {0L, 999L})
    void validateFenbeitongAssistantTicketUsesIssuingTenantAndRestoresContext(Long incomingTenant) {
        TenantContextHolder.setTenantId(incomingTenant);
        TenantContextHolder.setIgnore(true);
        var request = new AuthFenbeitongAssistantTicketValidateReqVO();
        request.setTicket("tenant-ticket");
        when(stringRedisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("fenbeitong_assistant_ticket:tenant-ticket"))
                .thenReturn(fenbeitongTenantPayload("169")).thenReturn(null);
        when(kingdeeConfigProvider.getCurrentConfigSnapshot()).thenAnswer(invocation -> {
            assertEquals(169L, TenantContextHolder.getRequiredTenantId());
            assertFalse(TenantContextHolder.isIgnore());
            return KingdeeConfigSnapshot.builder().acctId("tenant-169-only").build();
        });

        var response = authController.validateFenbeitongAssistantTicket(request).getData();

        assertTrue(response.getValid());
        assertEquals("tenant-169-only", response.getKingdeeConfig().getAcctId());
        assertEquals(incomingTenant, TenantContextHolder.getTenantId());
        assertTrue(TenantContextHolder.isIgnore());
        assertFalse(authController.validateFenbeitongAssistantTicket(request).getData().getValid());
        verify(kingdeeConfigProvider).getCurrentConfigSnapshot();
    }

    @ParameterizedTest
    @ValueSource(strings = {"null", "-1"})
    void validateFenbeitongAssistantTicketRejectsUntrustedTenantWithoutReadingConfig(String tenant) {
        var request = new AuthFenbeitongAssistantTicketValidateReqVO();
        request.setTicket("invalid-tenant-ticket");
        when(stringRedisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("fenbeitong_assistant_ticket:invalid-tenant-ticket"))
                .thenReturn(fenbeitongTenantPayload(tenant));

        var response = authController.validateFenbeitongAssistantTicket(request).getData();

        assertFalse(response.getValid());
        assertEquals("malformed", response.getReason());
        assertEquals(null, TenantContextHolder.getTenantId());
        verify(kingdeeConfigProvider, never()).getCurrentConfigSnapshot();
    }

    @Test
    void validateFenbeitongAssistantTicketRestoresContextWhenConfigFails() {
        TenantContextHolder.setTenantId(999L);
        TenantContextHolder.setIgnore(true);
        var request = new AuthFenbeitongAssistantTicketValidateReqVO();
        request.setTicket("config-failure-ticket");
        when(stringRedisTemplate.opsForValue()).thenReturn(valueOperations);
        when(valueOperations.get("fenbeitong_assistant_ticket:config-failure-ticket"))
                .thenReturn(fenbeitongTenantPayload("169"));
        when(kingdeeConfigProvider.getCurrentConfigSnapshot()).thenAnswer(invocation -> {
            assertEquals(169L, TenantContextHolder.getRequiredTenantId());
            assertFalse(TenantContextHolder.isIgnore());
            throw new ServiceException(400, "分贝通费用报销助手 ERP 配置缺失：appId");
        });

        var error = assertThrows(ServiceException.class,
                () -> authController.validateFenbeitongAssistantTicket(request));

        assertEquals(400, error.getCode());
        assertEquals(999L, TenantContextHolder.getTenantId());
        assertTrue(TenantContextHolder.isIgnore());
    }

    private static String fenbeitongTenantPayload(String tenant) {
        return "{\\"userId\\":303,\\"tenantId\\":" + tenant
                + ",\\"permissions\\":[\\"erp:fenbeitong-voucher:query\\"],\\"expiresAtEpochMilli\\":"
                + (System.currentTimeMillis() + 60_000L) + "}";
    }

'''
s=s.replace(marker,new+marker)
p.write_text(s,encoding='utf-8')
assert p.read_text(encoding='utf-8')==s
print('Regression scenarios prepared; production files unchanged')
