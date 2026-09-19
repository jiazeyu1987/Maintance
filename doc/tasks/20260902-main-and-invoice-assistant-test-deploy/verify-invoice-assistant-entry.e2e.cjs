const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')

const TASK_DIR = __dirname
const RESULT_DIR = path.join(TASK_DIR, 'artifacts', 'invoice-assistant-entry-e2e')
const REQUIRED_PERMISSION = 'erp:invoice-voucher-print:query'
const EXPECTED_MENU_PATH = 'invoice-voucher-print'
const EXPECTED_COMPONENT = 'erp/finance/invoice-voucher-print/index'

function envText(name, fallback = '') {
  const value = process.env[name]
  return typeof value === 'string' && value.trim() ? value.trim() : fallback
}

function collectConfig() {
  const config = {
    baseUrl: envText('INVOICE_ASSISTANT_E2E_BASE_URL', 'http://172.30.30.58:8081').replace(/\/+$/, ''),
    assistantUrl: envText('INVOICE_ASSISTANT_E2E_ASSISTANT_URL', 'http://172.30.30.58:18733').replace(/\/+$/, ''),
    tenant: envText('INVOICE_ASSISTANT_E2E_TENANT', '测试租户'),
    username: envText('INVOICE_ASSISTANT_E2E_USERNAME', 'aoteman'),
    password: envText('INVOICE_ASSISTANT_E2E_PASSWORD'),
    headed: envText('INVOICE_ASSISTANT_E2E_HEADED') === '1'
  }

  const missing = []
  if (!config.password) {
    missing.push({
      name: 'INVOICE_ASSISTANT_E2E_PASSWORD',
      description: '测试服真实登录密码，必须由当前进程注入，不得写入脚本或任务记录。'
    })
  }
  if (missing.length > 0) {
    writeResult({
      status: 'BLOCKED',
      reason: 'missing-prerequisite',
      missing,
      impact: '无法执行测试服真实登录和发票助手 iframe 验收。'
    })
    throw new Error(`Missing E2E prerequisite: ${missing.map((item) => item.name).join(', ')}`)
  }

  assert.equal(config.tenant, '测试租户', '真实 E2E 必须使用测试租户。')
  assert.equal(config.username, 'aoteman', '真实 E2E 必须使用 aoteman。')
  return config
}

function writeResult(result) {
  fs.mkdirSync(RESULT_DIR, { recursive: true })
  fs.writeFileSync(
    path.join(RESULT_DIR, 'result.json'),
    `${JSON.stringify({ ...result, verifiedAt: new Date().toISOString() }, null, 2)}\n`,
    'utf8'
  )
}

function loadPlaywright() {
  const packagePath = envText(
    'INVOICE_ASSISTANT_E2E_PLAYWRIGHT_PACKAGE',
    'D:\\IntRuoyiWorktree\\r260902c\\a\\IntRuoyiFronted\\node_modules\\playwright'
  )
  if (!fs.existsSync(packagePath)) {
    throw new Error(`Playwright package not found: ${packagePath}`)
  }
  return require(packagePath)
}

async function settle(page) {
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => undefined)
  await page.waitForTimeout(500)
}

async function fillFirstVisible(locator, value, label) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const item = locator.nth(index)
    if (await item.isVisible()) {
      await item.fill(value)
      return
    }
  }
  throw new Error(`No visible input found for ${label}`)
}

async function fillFirstVisibleIfPresent(locator, value) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const item = locator.nth(index)
    if (await item.isVisible()) {
      await item.fill(value)
      return true
    }
  }
  return false
}

async function readSelectedTenant(page) {
  const tenantField = page.locator('.login-form .el-form-item').filter({
    has: page.locator('.el-select')
  }).first()
  if ((await tenantField.count()) > 0 && (await tenantField.isVisible())) {
    return (await tenantField.innerText()).trim()
  }
  const tenantInput = page.locator('input[placeholder="请输入租户名称"]').first()
  return (await tenantInput.count()) > 0 ? (await tenantInput.inputValue()).trim() : ''
}

async function selectTenant(page, tenant) {
  const tenantSelect = page.locator('.login-form:visible .el-select').first()
  if ((await tenantSelect.count()) === 0 || !(await tenantSelect.isVisible())) {
    const filled = await fillFirstVisibleIfPresent(page.locator('input[placeholder="请输入租户名称"]'), tenant)
    if (!filled) {
      throw new Error('登录页租户控件不可见。')
    }
    return
  }

  await tenantSelect.click()
  const input = page
    .locator('.login-form:visible .el-select input[role="combobox"], .login-form:visible input.el-select__input')
    .first()
  await input.fill(tenant)
  const option = page.locator('.el-select-dropdown__item:visible').filter({ hasText: tenant }).first()
  await option.waitFor({ state: 'visible', timeout: 10000 })
  await option.click()

  const deadline = Date.now() + 5000
  while (Date.now() < deadline) {
    if ((await readSelectedTenant(page)).includes(tenant)) {
      return
    }
    await page.waitForTimeout(100)
  }
  throw new Error(`登录页租户未选中 ${tenant}。`)
}

async function readCommonResponse(response, label) {
  if (!response.ok()) {
    throw new Error(`${label} HTTP ${response.status()} from ${response.url()}`)
  }
  const payload = await response.json()
  const code = Number(payload && payload.code)
  if (Number.isFinite(code) && code !== 0 && code !== 200) {
    throw new Error(`${label} failed with code=${payload.code}, msg=${payload.msg || payload.message || ''}`)
  }
  return payload
}

function flattenMenus(menus, output = []) {
  for (const menu of Array.isArray(menus) ? menus : []) {
    output.push(menu)
    flattenMenus(menu.children, output)
  }
  return output
}

async function login(page, config) {
  await page.goto(`${config.baseUrl}/login?redirect=/index`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  })
  await settle(page)

  if (!page.url().includes('/login')) {
    return null
  }

  if ((await page.locator('.login-form img').count()) > 0) {
    throw new Error('登录页出现验证码，当前真实 E2E 不能无人值守执行。')
  }

  await selectTenant(page, config.tenant)
  await fillFirstVisible(page.locator('input[placeholder="请输入用户名"]'), config.username, 'username')
  await fillFirstVisible(page.locator('input[placeholder="请输入密码"]'), config.password, 'password')

  const permissionPromise = page.waitForResponse(
    (response) => response.url().includes('/admin-api/system/auth/get-permission-info'),
    { timeout: 60000 }
  )
  const loginError = page.locator('.el-message, .el-notification').filter({ hasText: /错误|失败|不存在|无效|密码/ }).last()
  await page.locator('.login-form:visible .el-button--primary, button:has-text("登录")').first().click()
  const loggedIn = await Promise.race([
    page.waitForURL((url) => !url.href.includes('/login'), { timeout: 60000 }).then(() => true),
    loginError.waitFor({ state: 'visible', timeout: 60000 }).then(() => false)
  ])
  if (!loggedIn) {
    const message = await loginError.textContent().catch(() => '')
    throw new Error(`测试租户登录失败：${message || 'unknown login error'}`)
  }

  const permissionPayload = await readCommonResponse(await permissionPromise, 'permission info')
  await settle(page)
  return permissionPayload.data || permissionPayload
}

function assertPermissionInfo(permissionInfo) {
  const permissions = Array.isArray(permissionInfo.permissions) ? permissionInfo.permissions : []
  assert.ok(permissions.includes(REQUIRED_PERMISSION), `权限响应缺少 ${REQUIRED_PERMISSION}`)
  const menus = flattenMenus(permissionInfo.menus)
  const menu = menus.find((item) => item && item.path === EXPECTED_MENU_PATH)
  assert.ok(menu, `权限菜单缺少 path=${EXPECTED_MENU_PATH}`)
  assert.equal(menu.component, EXPECTED_COMPONENT, `菜单 component 必须为 ${EXPECTED_COMPONENT}`)
  assert.equal(menu.componentName || menu.component_name, 'ErpInvoiceVoucherPrint')
}

async function clickVisibleMenuText(page, text) {
  const item = page
    .locator('.el-menu-item:visible, .el-sub-menu__title:visible, .v-menu__title:visible')
    .filter({ hasText: text })
    .first()
  await item.waitFor({ state: 'visible', timeout: 30000 })
  await item.click()
}

async function openInvoiceAssistantFromMenu(page, config) {
  await page.goto(`${config.baseUrl}/index`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  })
  await settle(page)
  await clickVisibleMenuText(page, 'ERP 系统')
  await clickVisibleMenuText(page, '财务管理')
  await clickVisibleMenuText(page, '发票凭证打印')
  await page.waitForURL(
    (url) => url.pathname === '/erp/finance/invoice-voucher-print',
    { timeout: 60000 }
  )
}

async function verifyDirectAccessGuard(browser, config) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, locale: 'zh-CN' })
  const page = await context.newPage()
  try {
    const response = await page.goto(`${config.assistantUrl}/`, { waitUntil: 'domcontentloaded', timeout: 60000 })
    assert.ok(response, '助手直连必须返回 HTTP 响应。')
    assert.equal(response.status(), 403, '助手直连必须返回 HTTP 403。')
    await page.locator('text=无权访问发票凭证打印助手').first().waitFor({ state: 'visible', timeout: 30000 })
    return { httpStatus: response.status(), blockedTextVisible: true }
  } finally {
    await context.close()
  }
}

async function verifyAssistantEntry(page, config) {
  const statusPromise = page.waitForResponse(
    (response) => response.url().includes('/admin-api/system/auth/invoice-voucher-print-assistant/status'),
    { timeout: 60000 }
  )
  const ticketPromise = page.waitForResponse(
    (response) =>
      response.url().includes('/admin-api/system/auth/invoice-voucher-print-ticket') &&
      response.request().method() === 'POST',
    { timeout: 60000 }
  )

  await openInvoiceAssistantFromMenu(page, config)

  const statusPayload = await readCommonResponse(await statusPromise, 'assistant status')
  const statusData = statusPayload.data || statusPayload
  assert.equal(statusData.running, true, `助手状态必须为 running，当前 message=${statusData.message || ''}`)

  const ticketPayload = await readCommonResponse(await ticketPromise, 'assistant ticket')
  const ticketData = ticketPayload.data || ticketPayload
  assert.ok(ticketData.ticket, '票据接口必须返回非空 ticket。')

  const frame = page.locator('iframe.invoice-voucher-print-frame[title="发票凭证打印"]').first()
  await frame.waitFor({ state: 'visible', timeout: 60000 })
  const src = await frame.getAttribute('src')
  assert.ok(src, '助手 iframe 必须有 src。')
  const srcUrl = new URL(src)
  const expectedUrl = new URL(config.assistantUrl)
  assert.equal(srcUrl.origin, expectedUrl.origin, '助手 iframe origin 必须指向配置的 18733 服务。')
  assert.equal(srcUrl.pathname, '/auth/callback', '助手 iframe 必须先进入 /auth/callback。')
  assert.ok(srcUrl.searchParams.get('ticket'), '助手 iframe callback 必须携带 ticket。')

  const assistantFrame = page.frameLocator('iframe.invoice-voucher-print-frame[title="发票凭证打印"]').first()
  await assistantFrame.locator('text=一键查询并生成打印包').first().waitFor({ state: 'visible', timeout: 60000 })
  await assistantFrame.locator('#previewButton').first().waitFor({ state: 'visible', timeout: 30000 })

  return {
    statusRunning: statusData.running === true,
    ticketPresent: Boolean(ticketData.ticket),
    iframeOrigin: srcUrl.origin,
    iframePath: srcUrl.pathname,
    callbackTicketPresent: Boolean(srcUrl.searchParams.get('ticket')),
    businessButtonVisible: true
  }
}

;(async () => {
  const config = collectConfig()
  const { chromium } = loadPlaywright()
  const browser = await chromium.launch({ headless: !config.headed })
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, locale: 'zh-CN' })
  const page = await context.newPage()
  const consoleErrors = []
  const pageErrors = []

  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })
  page.on('pageerror', (error) => pageErrors.push(error.message))

  try {
    const directGuard = await verifyDirectAccessGuard(browser, config)
    const permissionInfo = await login(page, config)
    assert.ok(permissionInfo, '登录后必须取得权限响应。')
    assertPermissionInfo(permissionInfo)
    const assistantEntry = await verifyAssistantEntry(page, config)

    assert.equal(consoleErrors.length, 0, `页面 console error 数必须为 0，当前 ${consoleErrors.length}`)
    assert.equal(pageErrors.length, 0, `页面 pageerror 数必须为 0，当前 ${pageErrors.length}`)

    const result = {
      status: 'PASS',
      baseUrl: config.baseUrl,
      assistantUrl: config.assistantUrl,
      tenant: config.tenant,
      username: config.username,
      permission: REQUIRED_PERMISSION,
      menuPath: EXPECTED_MENU_PATH,
      directGuard,
      assistantEntry,
      consoleErrorCount: consoleErrors.length,
      pageErrorCount: pageErrors.length
    }
    writeResult(result)
    console.log(`PASS: invoice assistant entry E2E baseUrl=${config.baseUrl} tenant=${config.tenant} username=${config.username}`)
  } catch (error) {
    writeResult({
      status: 'FAIL',
      baseUrl: config.baseUrl,
      assistantUrl: config.assistantUrl,
      tenant: config.tenant,
      username: config.username,
      error: error instanceof Error ? error.message : String(error),
      consoleErrorCount: consoleErrors.length,
      pageErrorCount: pageErrors.length
    })
    throw error
  } finally {
    await context.close()
    await browser.close()
  }
})().catch((error) => {
  console.error(error && error.stack ? error.stack : error)
  process.exitCode = 1
})
