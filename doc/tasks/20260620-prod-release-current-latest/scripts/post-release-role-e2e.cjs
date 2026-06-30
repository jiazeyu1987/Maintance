const fs = require('fs')
const path = require('path')
const { createRequire } = require('module')

const frontendRequire = createRequire(path.join('D:/ProjectPackage/Int/IntRuoyi/yudao-ui-admin-vue3', 'package.json'))
const { chromium } = frontendRequire('playwright')

const taskId = '20260620-prod-release-current-latest'
const taskDir = path.resolve(__dirname, '..')
const evidenceDir = path.join(taskDir, 'evidence')
const baseUrl = (process.env.POST_RELEASE_ROLE_E2E_BASE_URL || 'http://172.30.30.58:8081').replace(/\/+$/, '')
const tenant = process.env.POST_RELEASE_ROLE_E2E_TENANT || '芋道源码'
const password = process.env.POST_RELEASE_ROLE_E2E_PASSWORD

if (!password) {
  throw new Error('Missing POST_RELEASE_ROLE_E2E_PASSWORD')
}

const accounts = [
  { username: 'gaomin', expectedRootName: '展厅', runSmoke: false, expectedRouteCount: 6 },
  { username: 'zhaojie', expectedRootName: '智能排产', runSmoke: true, expectedRouteCount: 6 },
  { username: 'wangsiyu', expectedRootName: 'DCC文控中心', runSmoke: false, expectedRouteCount: 16 }
]

const forbiddenTexts = ['Access Denied', '权限不足', '无权访问', '页面不存在', '系统异常', '404 Not Found']

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true })
}

function now() {
  return new Date().toISOString()
}

function textSnippet(text, limit = 300) {
  return String(text || '').replace(/\s+/g, ' ').trim().slice(0, limit)
}

async function settle(page, timeout = 12000) {
  await page.waitForLoadState('domcontentloaded', { timeout }).catch(() => {})
  await page.waitForLoadState('networkidle', { timeout }).catch(() => {})
  await page.waitForTimeout(500)
}

async function fillFirstVisible(locator, value, label) {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    const input = locator.nth(index)
    if (await input.isVisible().catch(() => false)) {
      await input.click().catch(() => {})
      await input.fill('')
      await input.fill(value)
      const actual = await input.inputValue().catch(() => '')
      if (actual !== value) {
        throw new Error(`${label} 输入回读不匹配: expected=${value}, actual=${actual}`)
      }
      return
    }
  }
  throw new Error(`未找到可见${label}输入框`)
}

async function selectTenant(form, page, tenantName) {
  const tenantSelect = form.locator('.el-select').first()
  if ((await tenantSelect.count()) === 0 || !(await tenantSelect.isVisible().catch(() => false))) {
    const directInput = form.locator('input[placeholder="请输入租户名称"]').first()
    if (await directInput.count()) {
      await directInput.fill(tenantName)
      return
    }
    throw new Error('登录页缺少租户输入框')
  }
  await tenantSelect.click()
  const input = form.locator('.el-select input[role="combobox"], input.el-select__input').first()
  await input.fill('')
  await input.fill(tenantName)
  const option = page.locator('.el-select-dropdown__item').filter({ hasText: tenantName }).first()
  if (await option.count()) {
    await option.click({ timeout: 5000 }).catch(async () => input.press('Enter'))
  } else {
    await input.press('Enter')
  }
}

async function login(page, account) {
  await page.goto(`${baseUrl}/login?redirect=${encodeURIComponent('/index')}`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  })
  await settle(page, 15000)
  const form = page.locator('form.login-form:visible').first()
  await form.waitFor({ state: 'visible', timeout: 30000 })
  await selectTenant(form, page, tenant)
  await fillFirstVisible(form.locator('input[placeholder="请输入用户名"], input[placeholder="请输入账号"]'), account.username, '用户名')
  await fillFirstVisible(form.locator('input[placeholder="请输入密码"], input[type="password"]'), password, '密码')
  const loginResponsePromise = page.waitForResponse(
    (response) => response.url().includes('/admin-api/system/auth/login') && response.request().method() === 'POST',
    { timeout: 60000 }
  )
  await form.getByRole('button', { name: '登录' }).click()
  const loginResponse = await loginResponsePromise
  const payload = await loginResponse.json().catch(async () => ({ raw: await loginResponse.text().catch(() => '') }))
  if (!loginResponse.ok() || ![0, 200].includes(payload.code)) {
    throw new Error(`登录失败: ${account.username}, http=${loginResponse.status()}, payload=${JSON.stringify(payload).slice(0, 500)}`)
  }
  await page.waitForURL((url) => !url.href.includes('/login'), { timeout: 60000 })
  await settle(page)
}

async function fetchMenuTree(page) {
  const cachedRouters = await page.evaluate(() => {
    const raw = localStorage.getItem('roleRouters')
    if (!raw) return null
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        return parsed
      }
      if (parsed && typeof parsed === 'object' && typeof parsed.v === 'string') {
        return JSON.parse(parsed.v)
      }
      return null
    } catch (error) {
      return null
    }
  }).catch(() => null)
  if (Array.isArray(cachedRouters) && cachedRouters.length) {
    return cachedRouters
  }

  const response = await page.waitForResponse(
    (resp) => resp.url().includes('/admin-api/system/menu/list') && resp.request().method() === 'GET',
    { timeout: 5000 }
  ).catch(() => null)
  if (response) {
    const json = await response.json().catch(() => null)
    if (Array.isArray(json?.data)) {
      return json.data
    }
  }
  return await page.evaluate(async () => {
    const res = await fetch('/admin-api/system/menu/list', {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json, text/plain, */*'
      }
    })
    const payload = await res.json().catch(() => null)
    if (!res.ok || !payload || !Array.isArray(payload.data)) {
      return null
    }
    return payload.data
  }).catch(() => null)
}

function normalizeRoutePath(routePath) {
  return routePath.startsWith('/') ? routePath : `/${routePath}`
}

function joinRoutePath(parentPath, childPath) {
  const normalizedChild = normalizeRoutePath(childPath)
  if (
    normalizedChild.startsWith('/mes/') ||
    normalizedChild.startsWith('/dcc/') ||
    normalizedChild.startsWith('/showroom/') ||
    normalizedChild.startsWith('/system/') ||
    normalizedChild.startsWith('/infra/') ||
    normalizedChild.startsWith('/bpm/')
  ) {
    return normalizedChild
  }
  const normalizedParent = normalizeRoutePath(parentPath || '')
  return `${normalizedParent.replace(/\/+$/, '')}${normalizedChild}`
}

function buildRootMenu(menuTree, expectedRootName) {
  const rootMenu = menuTree.find((item) => item.name === expectedRootName)
  if (!rootMenu) return null
  return {
    id: rootMenu.id,
    name: rootMenu.name,
    path: rootMenu.path,
    component: rootMenu.component || '',
    childCount: Array.isArray(rootMenu.children) ? rootMenu.children.length : 0,
    children: (rootMenu.children || []).map((item) => ({
      id: item.id,
      name: item.name,
      path: joinRoutePath(rootMenu.path, item.path),
      component: item.component || '',
      permission: item.permission || ''
    }))
  }
}

async function readTopMenus(page) {
  const routers = await fetchMenuTree(page)
  if (Array.isArray(routers) && routers.length) {
    return routers.map((item) => item.name).filter(Boolean)
  }
  return []
}

function createWatchers(page) {
  const requestFailures = []
  const consoleErrors = []
  const pageErrors = []
  const apiFailures = []

  const onRequestFailed = (request) => {
    const item = {
      method: request.method(),
      url: request.url(),
      failure: request.failure()?.errorText || ''
    }
    const benign =
      /https:\/\/hm\.baidu\.com\//.test(item.url) ||
      /https:\/\/api\.iconify\.design\//.test(item.url) ||
      (item.url.includes('/admin-api/system/notify-message/get-unread-count') && item.failure === 'net::ERR_ABORTED') ||
      (item.url.includes('/admin-api/system/dict-data/simple-list') && item.failure === 'net::ERR_ABORTED')
    requestFailures.push({ ...item, benign })
  }
  const onConsole = (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text())
    }
  }
  const onPageError = (error) => {
    pageErrors.push(error.message)
  }
  const onResponse = async (response) => {
    if (!response.url().startsWith(baseUrl) || !response.url().includes('/admin-api/')) return
    if (response.status() < 400) return
    apiFailures.push({
      method: response.request().method(),
      url: response.url(),
      status: response.status()
    })
  }

  page.on('requestfailed', onRequestFailed)
  page.on('console', onConsole)
  page.on('pageerror', onPageError)
  page.on('response', onResponse)

  return {
    requestFailures,
    consoleErrors,
    pageErrors,
    apiFailures,
    detach() {
      page.off('requestfailed', onRequestFailed)
      page.off('console', onConsole)
      page.off('pageerror', onPageError)
      page.off('response', onResponse)
    }
  }
}

async function visitRoute(page, child) {
  const routeWatchers = createWatchers(page)
  try {
    await page.goto(`${baseUrl}${child.path}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    })
    await settle(page)
    const bodyText = await page.locator('body').innerText().catch(() => '')
    return {
      id: child.id,
      name: child.name,
      path: child.path,
      component: child.component,
      permission: child.permission,
      startedAt: now(),
      finalUrl: page.url(),
      title: await page.title(),
      forbiddenTexts: forbiddenTexts.filter((item) => bodyText.includes(item)),
      apiFailures: routeWatchers.apiFailures,
      requestFailures: routeWatchers.requestFailures.filter((item) => !item.benign && item.url.startsWith(baseUrl)),
      externalRequestFailures: routeWatchers.requestFailures.filter((item) => item.benign || !item.url.startsWith(baseUrl)),
      consoleErrors: routeWatchers.consoleErrors,
      pageErrors: routeWatchers.pageErrors,
      screenshot: ''
    }
  } finally {
    routeWatchers.detach()
  }
}

async function runSmoke(page) {
  const smoke = {
    startedAt: now(),
    statuses: [],
    clickedStart: false,
    completed: false
  }
  await page.goto(`${baseUrl}/mes/pro/scheduler-workbench`, {
    waitUntil: 'domcontentloaded',
    timeout: 60000
  })
  await settle(page)

  const expanded = await page.evaluate(() => {
    const details = document.querySelector('.scheduler-workbench__test-panel')
    if (!details) return false
    details.open = true
    return true
  }).catch(() => false)
  if (expanded) {
    await page.waitForTimeout(300)
  }

  const bodyBefore = await page.locator('body').innerText().catch(() => '')
  smoke.statuses.push({
    phase: 'before-start',
    text: textSnippet(bodyBefore, 200)
  })

  const clicked = await page.evaluate(() => {
    const visible = (element) => {
      const rect = element.getBoundingClientRect()
      const style = window.getComputedStyle(element)
      return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden'
    }
    const buttons = Array.from(document.querySelectorAll('button')).filter(visible)
    const target = buttons.find((button) => /开始冒烟测试|启动冒烟测试|开始冒烟|启动冒烟|运行冒烟|开始运行/.test((button.innerText || '').replace(/\s+/g, ' ').trim()))
    if (!target) {
      return { clicked: false, buttons: buttons.map((button) => (button.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 40) }
    }
    target.click()
    return { clicked: true, text: (target.innerText || '').replace(/\s+/g, ' ').trim() }
  }).catch(() => ({ clicked: false, buttons: [] }))
  smoke.clickedStart = !!clicked.clicked
  if (!clicked.clicked) {
    smoke.statuses.push({
      phase: 'start-miss',
      text: `未找到 smoke 启动按钮，可见按钮: ${(clicked.buttons || []).join(' | ')}`
    })
  } else {
    await page.waitForTimeout(1000)
  }

  for (let index = 0; index < 45; index += 1) {
    await page.waitForTimeout(7000)
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 }).catch(() => {})
    await settle(page)
    const bodyText = await page.locator('body').innerText().catch(() => '')
    const matchedLine = bodyText
      .split('\n')
      .map((item) => item.trim())
      .find((item) => /未启动|运行中|已结束|完成|失败|PASS|FAIL/.test(item))
    const snapshot = textSnippet(matchedLine || bodyText, 240)
    smoke.statuses.push({ phase: 'poll', text: snapshot, at: now() })
    if (/已结束|完成|PASS/.test(snapshot)) {
      smoke.completed = true
      break
    }
    if (/失败|FAIL/.test(snapshot)) {
      break
    }
  }
  return smoke
}

async function runAccount(browser, account) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  const page = await context.newPage()
  const watchers = createWatchers(page)
  const result = {
    username: account.username,
    expectedRootName: account.expectedRootName,
    startedAt: now(),
    topMenus: [],
    sidebarTexts: [],
    rootMenu: null,
    routes: [],
    smoke: null,
    failures: [],
    finishedAt: null
  }

  try {
    await login(page, account)
    const menuTree = await fetchMenuTree(page)
    if (!menuTree) {
      result.failures.push('未捕获 menu/list 响应')
      return result
    }

    result.topMenus = await readTopMenus(page)
    if (result.topMenus.length !== 1 || result.topMenus[0] !== account.expectedRootName) {
      result.failures.push(`顶层菜单不符合预期: ${JSON.stringify(result.topMenus)}`)
    }

    const rootMenu = buildRootMenu(menuTree, account.expectedRootName)
    if (!rootMenu) {
      result.failures.push(`未找到根菜单: ${account.expectedRootName}`)
      return result
    }
    result.rootMenu = {
      id: rootMenu.id,
      name: rootMenu.name,
      path: rootMenu.path,
      component: rootMenu.component,
      childCount: rootMenu.childCount
    }
    result.sidebarTexts = rootMenu.children.map((item) => item.name)
    if (rootMenu.childCount !== account.expectedRouteCount) {
      result.failures.push(`根菜单子页数量不符合预期: expected=${account.expectedRouteCount}, actual=${rootMenu.childCount}`)
    }

    for (const child of rootMenu.children) {
      const routeResult = await visitRoute(page, child)
      result.routes.push(routeResult)
      if (
        routeResult.forbiddenTexts.length ||
        routeResult.apiFailures.length ||
        routeResult.requestFailures.length ||
        routeResult.consoleErrors.length ||
        routeResult.pageErrors.length
      ) {
        result.failures.push(`子页失败: ${child.name}`)
      }
    }

    if (account.runSmoke) {
      result.smoke = await runSmoke(page)
      if (!result.smoke.completed) {
        result.failures.push('智能排产冒烟测试未完成')
      }
    }

    const blockingGlobalRequests = watchers.requestFailures.filter((item) => !item.benign && item.url.startsWith(baseUrl))
    if (blockingGlobalRequests.length) {
      result.failures.push(`全局 requestfailed ${blockingGlobalRequests.length} 条`)
    }
    if (watchers.consoleErrors.length) {
      result.failures.push(`全局 console error ${watchers.consoleErrors.length} 条`)
    }
    if (watchers.pageErrors.length) {
      result.failures.push(`全局 page error ${watchers.pageErrors.length} 条`)
    }
    return result
  } finally {
    result.finishedAt = now()
    watchers.detach()
    await context.close()
  }
}

async function main() {
  ensureDir(evidenceDir)
  const browser = await chromium.launch({ headless: true })
  const run = {
    taskId,
    startedAt: now(),
    baseUrl,
    tenant,
    accounts: accounts.map(({ username, expectedRootName, runSmoke }) => ({ username, expectedRootName, runSmoke })),
    results: [],
    failures: [],
    finishedAt: null,
    status: 'RUNNING'
  }

  try {
    for (const account of accounts) {
      const result = await runAccount(browser, account)
      run.results.push(result)
      if (result.failures.length) {
        run.failures.push(...result.failures.map((item) => `${account.username}: ${item}`))
      }
    }
    run.status = run.failures.length ? 'FAIL' : 'PASS'
  } finally {
    run.finishedAt = now()
    const outputPath = path.join(evidenceDir, `post-release-role-e2e-${Date.now()}.json`)
    fs.writeFileSync(outputPath, JSON.stringify(run, null, 2), 'utf8')
    await browser.close()
    console.log(outputPath)
    console.log(JSON.stringify({ status: run.status, failureCount: run.failures.length }, null, 2))
    if (run.failures.length) {
      process.exitCode = 1
    }
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
